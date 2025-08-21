from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import openai
import os
import logging
import random
import time
from typing import Any, Optional, Sequence, Mapping, TypeGuard, List, Union
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
    "deepseek-chat": 126000
}


class OpenaiLanguageModel(LanguageModel):
    """
    To keep the name of the class consistent with the name of file, use OpenaiAgent instead of OpenAIAgent.
    """

    def __init__(
        self,
        role_dict: Mapping[str, str],
        api_configs: Optional[List[Mapping[str, str]]] = None,
        model_name: Optional[str] = None,
        api_key: Optional[Union[str, List[str]]] = None,
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

        if api_configs:
            self.api_configs = api_configs
        elif model_name:
            if isinstance(api_key, str) or api_key is None:
                api_keys = [api_key]
            else:
                api_keys = api_key

            self.api_configs = [
                {
                    "model_name": model_name,
                    "api_key": key or os.environ.get("OPENAI_API_KEY"),
                    "base_url": base_url or os.environ.get("OPENAI_BASE_URL"),
                }
                for key in api_keys
            ]
        else:
            raise ValueError("Either 'api_configs' or 'model_name' must be provided.")

        self.clients = [
            OpenAI(api_key=config.get("api_key"), base_url=config.get("base_url"))
            for config in self.api_configs
        ]
        self.current_api_index = 0

        self.model_names = [config["model_name"] for config in self.api_configs]
        self.model_name = self.model_names[0]

        self.maximum_prompt_token_counts = {
            m_name: OpenaiLanguageModel._get_max_context_length(m_name)
            for m_name in self.model_names
        }

        if maximum_prompt_token_count is None:
            self.maximum_prompt_token_count = min(
                self.maximum_prompt_token_counts.values()
            )
        else:
            self.maximum_prompt_token_count = maximum_prompt_token_count

        retry_config = retry_config or {}
        self.max_retries = retry_config.get("max_retries", 3)
        self.backoff_multiplier = retry_config.get("multiplier", 2.0)
        self.min_wait = retry_config.get("min_wait", 1)
        self.max_wait = retry_config.get("max_wait", 60)
        self.infinite_for_rate_limit = retry_config.get(
            "infinite_for_rate_limit", True
        )
        self.encodings = {}
        for model in self.model_names:
            try:
                self.encodings[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                logging.warning(
                    f"Model {model} not found in tiktoken. Using cl100k_base encoding."
                )
                self.encodings[model] = tiktoken.get_encoding("cl100k_base")
        self.encoding = self.encodings[self.model_name]

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
        api_failures = 0

        while True:
            client = self.clients[self.current_api_index]
            model_name = self.model_names[self.current_api_index]
            try:
                truncated_message_list = self._truncate_message_list(
                    message_list, model_name
                )
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=truncated_message_list,
                    **inference_config_dict,
                )
                break  # Success
            except openai.APIError as e:
                # Handle non-recoverable context length error first
                if isinstance(e, openai.BadRequestError) and "context length" in str(e):
                    raise LanguageModelContextLimitException(
                        f"Model {model_name} reaches the context limit."
                    ) from e

                logging.warning(
                    f"API call failed for API index {self.current_api_index} with error: {e}. Switching to next API."
                )
                self.current_api_index = (self.current_api_index + 1) % len(self.api_configs)
                api_failures += 1

                if api_failures >= len(self.api_configs):
                    # A full cycle of API failures has occurred. Start retrying with backoff.
                    retries += 1
                    # Special handling for rate limit errors with infinite retries
                    is_rate_limit_error = isinstance(e, openai.RateLimitError)
                    max_retries_reached = (not (self.infinite_for_rate_limit and is_rate_limit_error)) and (retries > self.max_retries)

                    if max_retries_reached:
                        logging.error(
                            f"All APIs failed after {retries - 1} full cycles. Failing. Last error: {e}"
                        )
                        raise e

                    logging.warning(
                        f"All APIs have failed in a cycle. Waiting for {wait_time:.2f} seconds before retrying."
                    )
                    time.sleep(wait_time)
                    api_failures = 0  # Reset failure count for the next cycle

                    wait_time = min(wait_time * self.backoff_multiplier, self.max_wait)
                    wait_time += random.uniform(0, 0.1) * wait_time  # Add jitter
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

    def _num_tokens_from_messages(
        self, messages: Sequence[ChatCompletionMessageParam], model: str
    ) -> int:
        # This implementation is based on the official OpenAI cookbook:
        # https://github.com/openai/openai-cookbook/blob/main/examples/how_to_count_tokens_with_tiktoken.ipynb
        encoding = self.encodings.get(model)
        if encoding is None:
            logging.warning(f"No encoding found for model {model}. Using default.")
            encoding = self.encoding

        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                if value is not None:
                    num_tokens += len(encoding.encode(str(value)))
                if key == "name":
                    num_tokens -= 1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    def _truncate_message_list(
        self, message_list: Sequence[ChatCompletionMessageParam], model_name: str
    ) -> Sequence[ChatCompletionMessageParam]:
        max_tokens = self.maximum_prompt_token_counts.get(
            model_name, self.maximum_prompt_token_count
        )
        if not max_tokens:
            return message_list

        num_tokens = self._num_tokens_from_messages(message_list, model_name)
        if num_tokens <= max_tokens:
            return message_list

        truncated_list = list(message_list)

        system_message = []
        if truncated_list and truncated_list[0]["role"] == "system":
            system_message = [truncated_list.pop(0)]

        while num_tokens > max_tokens and truncated_list:
            truncated_list.pop(0)
            num_tokens = self._num_tokens_from_messages(
                system_message + truncated_list, model_name
            )

        final_list = system_message + truncated_list

        final_tokens = self._num_tokens_from_messages(final_list, model_name)
        logging.warning(
            f"Input has been truncated due to context length limit. "
            f"Original token count: {self._num_tokens_from_messages(message_list, model_name)}, "
            f"Truncated token count: {final_tokens}, "
            f"Max tokens: {max_tokens}"
        )

        return final_list
