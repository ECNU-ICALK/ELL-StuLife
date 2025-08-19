from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import openai
import os
import logging
import random
import time
from typing import Any, Optional, Sequence, Mapping, TypeGuard
import tiktoken

from src.language_models.language_model import LanguageModel
from src.typings import (
    Role,
    ChatHistoryItem,
    LanguageModelContextLimitException,
    ChatHistory,
)
from src.utils import RetryHandler, ExponentialBackoffStrategy


MODEL_CONTEXT_LENGTHS = {
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo-0125": 16385,
    "gpt-3.5-turbo": 4096,
}


class OpenaiLanguageModel(LanguageModel):
    """
    To keep the name of the class consistent with the name of file, use OpenaiAgent instead of OpenAIAgent.
    """

    def __init__(
        self,
        model_name: str,
        role_dict: Mapping[str, str],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        maximum_prompt_token_count: Optional[int] = None,
        retry_config: Optional[Mapping[str, Any]] = None,
    ):
        """
        max_prompt_tokens: The maximum number of tokens that can be used in the prompt. It can be used to set the
            context limit manually. If it is set to None, the context limit will be the same as the context length of
            the model selected.
        retry_config: A dict to configure retry behavior.
            max_retries (int): Maximum number of retries. Default 3.
            multiplier (float): Multiplier for exponential backoff. Default 2.0.
            min_wait (int): Minimum wait time in seconds. Default 1.
            max_wait (int): Maximum wait time in seconds. Default 60.
            infinite_for_rate_limit (bool): Whether to retry indefinitely on RateLimitError. Default True.
        """
        super().__init__(role_dict)
        self.model_name = model_name
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.maximum_prompt_token_count = maximum_prompt_token_count
        if self.maximum_prompt_token_count is None:
            self.maximum_prompt_token_count = (
                OpenaiLanguageModel._get_max_context_length(model_name)
            )

        retry_config = retry_config or {}
        self.max_retries = retry_config.get("max_retries", 3)
        self.backoff_multiplier = retry_config.get("multiplier", 2.0)
        self.min_wait = retry_config.get("min_wait", 1)
        self.max_wait = retry_config.get("max_wait", 60)
        self.infinite_for_rate_limit = retry_config.get(
            "infinite_for_rate_limit", True
        )

        try:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            logging.warning(
                f"Model {self.model_name} not found in tiktoken. Using cl100k_base encoding."
            )
            self.encoding = tiktoken.get_encoding("cl100k_base")

    @staticmethod
    def _get_max_context_length(model_name: str) -> int:
        if model_name in MODEL_CONTEXT_LENGTHS:
            return MODEL_CONTEXT_LENGTHS[model_name]
        for base_model, length in MODEL_CONTEXT_LENGTHS.items():
            if model_name.startswith(base_model):
                return length
        logging.warning(f"Could not determine context length for model {model_name}. "
                        f"Defaulting to 4096. Please specify `maximum_prompt_token_count` for this model.")
        return 4096

    @staticmethod
    def _is_valid_message_list(
        message_list: list[Mapping[str, str]],
    ) -> TypeGuard[list[ChatCompletionMessageParam]]:
        for message_dict in message_list:
            if (
                "role" not in message_dict.keys()
                or "content" not in message_dict.keys()
            ):
                return False
        return True

    def _get_completion_content(
        self,
        message_list: Sequence[ChatCompletionMessageParam],
        inference_config_dict: Mapping[str, Any],
    ) -> Sequence[str]:
        """
        I do not know what will happen when the context limit is reached. According to OpenAI documents, there is no
        type of error for the context limit. So I guess the model will return an empty response when the context limit
        is reached. This may be a potential bug and I apologize in advance.
        There are also some issues on GitHub state that the model will raise openai.BadRequestError in this situation.
        So I also handle this error in the code.
        Reference:
        https://platform.openai.com/docs/guides/error-codes#python-library-error-types
        https://github.com/run-llama/llama_index/discussions/11889
        """
        retries = 0
        wait_time = float(self.min_wait)

        while True:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=message_list,
                    **inference_config_dict,
                )
                break  # Success
            except openai.RateLimitError as e:
                if not self.infinite_for_rate_limit and retries >= self.max_retries:
                    logging.error(f"Rate limit error and max retries reached. Failing. Error: {e}")
                    raise e
                
                logging.warning(f"Rate limit error encountered. Retrying in {wait_time:.2f} seconds. Error: {e}")
                time.sleep(wait_time)
                
                if not self.infinite_for_rate_limit:
                    retries += 1
                
                wait_time = min(wait_time * self.backoff_multiplier, self.max_wait)
                wait_time += random.uniform(0, 0.1) * wait_time  # Jitter
            
            except openai.BadRequestError as e:
                if "context length" in str(e):
                    # Raise LanguageModelContextLimitException to skip retrying.
                    raise LanguageModelContextLimitException(
                        f"Model {self.model_name} reaches the context limit. "
                    ) from e

                if retries >= self.max_retries:
                    logging.error(f"Bad request error and max retries reached. Failing. Error: {e}")
                    raise e

                retries += 1
                logging.warning(f"Bad request error encountered. Retrying in {wait_time:.2f} seconds. Error: {e}")
                time.sleep(wait_time)
                wait_time = min(wait_time * self.backoff_multiplier, self.max_wait)
                wait_time += random.uniform(0, 0.1) * wait_time  # Jitter

        if (
            completion.usage is not None
            and self.maximum_prompt_token_count is not None
            and completion.usage.prompt_tokens > self.maximum_prompt_token_count
        ):
            raise LanguageModelContextLimitException(
                f"Model {self.model_name} reaches the context limit. "
                f"Current prompt tokens: {completion.usage.prompt_tokens}. "
                f"Max prompt tokens: {self.maximum_prompt_token_count}."
            )
        content_list: list[str] = []
        content_all_invalid_flag: bool = True
        for choice in completion.choices:
            content = choice.message.content
            if content is not None and len(content) > 0:
                content_all_invalid_flag = False
            content_list.append(content or "")
        if content_all_invalid_flag:
            raise LanguageModelContextLimitException(
                f"Model {self.model_name} returns empty response. The context limit may be reached."
            )
        return content_list

    def _inference(
        self,
        batch_chat_history: Sequence[ChatHistory],
        inference_config_dict: Mapping[str, Any],
        system_prompt: str,
    ) -> Sequence[ChatHistoryItem]:
        """
        system_prompt: It is usually called as system_prompt. But in OpenAI documents, it is called as developer_prompt.
            But in practice, using `message_list = [{"role": "developer", "content": self.system_prompt}]` will raise an
            error. So all after all, I call it as system_prompt.
            Reference:
            https://platform.openai.com/docs/guides/text-generation#messages-and-roles
            https://platform.openai.com/docs/api-reference/chat/create
        inference_config_dict: Other config for OpenAI().chat.completions.create.
            e.g.:
            max_completion_tokens: The maximum number of tokens that can be generated in the chat completion. Notice
                that max_tokens is deprecated.
            Reference:
            https://platform.openai.com/docs/api-reference/chat/create#chat-create-max_completion_tokens
        """
        # region Construct batch_message_list
        message_list_prefix: list[ChatCompletionMessageParam]
        if len(system_prompt) > 0:
            message_list_prefix = [{"role": "system", "content": system_prompt}]
        else:
            message_list_prefix = []
        batch_message_list: list[Sequence[ChatCompletionMessageParam]] = []
        for chat_history in batch_chat_history:
            conversion_result = self._convert_chat_history_to_message_list(chat_history)
            assert OpenaiLanguageModel._is_valid_message_list(conversion_result)
            batch_message_list.append(message_list_prefix + conversion_result)
        # endregion
        # region Generate output
        output_str_list: list[str] = []
        for message_list in batch_message_list:
            message_list = self._truncate_message_list(message_list)
            output_str_list.extend(
                self._get_completion_content(message_list, inference_config_dict)
            )
        # endregion
        # region Convert output to ChatHistoryItem
        return [
            ChatHistoryItem(role=Role.AGENT, content=output_str)
            for output_str in output_str_list
        ]
        # endregion

    def _num_tokens_from_messages(self, messages: Sequence[ChatCompletionMessageParam]) -> int:
        # This implementation is based on the official OpenAI cookbook:
        # https://github.com/openai/openai-cookbook/blob/main/examples/how_to_count_tokens_with_tiktoken.ipynb
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                if value is not None:
                    num_tokens += len(self.encoding.encode(str(value)))
                if key == "name":
                    num_tokens -= 1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    def _truncate_message_list(self, message_list: Sequence[ChatCompletionMessageParam]) -> Sequence[ChatCompletionMessageParam]:
        if not self.maximum_prompt_token_count:
            return message_list

        num_tokens = self._num_tokens_from_messages(message_list)
        if num_tokens <= self.maximum_prompt_token_count:
            return message_list

        truncated_list = list(message_list)
        
        system_message = []
        if truncated_list and truncated_list[0]['role'] == 'system':
            system_message = [truncated_list.pop(0)]

        while num_tokens > self.maximum_prompt_token_count and truncated_list:
            truncated_list.pop(0)
            num_tokens = self._num_tokens_from_messages(system_message + truncated_list)

        final_list = system_message + truncated_list
        
        final_tokens = self._num_tokens_from_messages(final_list)
        logging.warning(
            f"Input has been truncated due to context length limit. "
            f"Original token count: {self._num_tokens_from_messages(message_list)}, "
            f"Truncated token count: {final_tokens}, "
            f"Max tokens: {self.maximum_prompt_token_count}"
        )
        
        return final_list
