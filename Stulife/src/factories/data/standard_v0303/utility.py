from pydantic import BaseModel
import datetime
import threading
import json
from typing import Any, Optional, Sequence, TypeVar, Generic, Mapping
import os
from openai.types.chat.chat_completion import ChatCompletion
import re
from openai import OpenAI
from abc import abstractmethod, ABC
from openai.types.chat import ChatCompletionMessageParam
import numpy as np
import random
from enum import StrEnum
import hashlib

from src.utils import SafeLogger, SingletonLogger
from src.typings import LoggerConfig
from src.tasks.task import SkillUtility


class ExclusiveJsonAccessUtility:
    _locks: dict[str, threading.Lock] = {}
    _locks_lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_lock(cls, file_path: str) -> threading.Lock:
        absolute_path = os.path.abspath(file_path)
        with cls._locks_lock:
            if absolute_path not in cls._locks:
                cls._locks[absolute_path] = threading.Lock()
            return cls._locks[absolute_path]

    def __init__(self, file_path: str):
        self.file_path = os.path.abspath(file_path)
        self._lock = self._get_lock(self.file_path)

    def __enter__(self) -> "ExclusiveJsonAccessUtility":
        self._lock.acquire()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._lock.release()

    def read(self) -> Any:
        with open(self.file_path, "r") as f:
            return json.load(f)

    def write(self, data: Any) -> None:
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)  # noqa


class GenerationException(Exception):
    pass


class OpenaiCompletionException(GenerationException):
    pass


class TokenUsageInfo(BaseModel):
    chat_completion: ChatCompletion
    # The following two fields are added to improve the readability of the output.
    created_time: str
    estimated_price: float

    @staticmethod
    def from_chat_completion(
        chat_completion: ChatCompletion,
    ) -> "TokenUsageInfo":
        created_timestamp = chat_completion.created
        created_time = datetime.datetime.fromtimestamp(created_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if chat_completion.usage is None:
            raise OpenaiCompletionException(
                "Cannot extract usage information from chat_completion."
            )
        estimated_price = TokenUsageInfo._estimate_api_price(
            created_timestamp,
            chat_completion.model,
            chat_completion.usage.prompt_tokens,
            chat_completion.usage.completion_tokens,
        )
        return TokenUsageInfo(
            chat_completion=chat_completion,
            created_time=created_time,
            estimated_price=estimated_price,
        )

    @staticmethod
    def log_and_create_from_chat_completion(
        chat_completion: ChatCompletion,
        token_usage_info_dict_json_access_utility: ExclusiveJsonAccessUtility,
    ) -> "TokenUsageInfo":
        original_token_info_list: list[TokenUsageInfo] = [
            TokenUsageInfo.model_validate(token_usage_info_dict)
            for token_usage_info_dict in token_usage_info_dict_json_access_utility.read()
        ]
        current_token_usage_info = TokenUsageInfo.from_chat_completion(chat_completion)
        new_token_info_list = original_token_info_list + [current_token_usage_info]
        token_usage_info_dict_json_access_utility.write(
            [token_info.model_dump() for token_info in new_token_info_list],
        )
        return current_token_usage_info

    @staticmethod
    def _estimate_api_price(
        created_timestamp: int,
        model_name: str,
        prompt_token_count: int,
        completion_token_count: int,
    ) -> float:
        model_name = model_name.lower()
        deepseek_discount_flag = TokenUsageInfo.is_deepseek_discount_active(
            created_timestamp
        )
        if "gpt-4o-mini" in model_name:
            price_per_prompt_token = 0.15 * 1e-6
            price_per_completion_token = 0.6 * 1e-6
        elif "gpt-4o-2024-08-06" in model_name:
            price_per_prompt_token = 2.5 * 1e-6
            price_per_completion_token = 10 * 1e-6
        elif "gpt-4o" in model_name:
            price_per_prompt_token = 2.5 * 1e-6
            price_per_completion_token = 10 * 1e-6
        elif "deepseek-chat" in model_name:
            price_per_prompt_token = 0.27 * 1e-6
            price_per_completion_token = 1.10 * 1e-6
            if deepseek_discount_flag:
                price_per_prompt_token = 0.135 * 1e-6
                price_per_completion_token = 0.550 * 1e-6
        elif "deepseek-reasoner" in model_name:
            price_per_prompt_token = 0.55 * 1e-6
            price_per_completion_token = 2.19 * 1e-6
            if deepseek_discount_flag:
                price_per_prompt_token = 0.135 * 1e-6
                price_per_completion_token = 0.550 * 1e-6
        else:
            price_per_prompt_token = price_per_completion_token = -1
        return (
            price_per_prompt_token * prompt_token_count
            + price_per_completion_token * completion_token_count
        )

    @staticmethod
    def is_deepseek_discount_active(timestamp: int) -> bool:
        dt = datetime.datetime.fromtimestamp(timestamp)
        deepseek_discount_start_time = dt.replace(
            hour=0, minute=30, second=0, microsecond=0
        )
        deepseek_discount_end_time = dt.replace(
            hour=8, minute=30, second=0, microsecond=0
        )
        return deepseek_discount_start_time <= dt <= deepseek_discount_end_time


class JSONObjectExtractionException(Exception):
    pass


class DataFactoryUtility:
    @staticmethod
    def extract_json_object_from_chat_completion_content(
        content: str, required_key_list: Optional[Sequence[str]] = None
    ) -> dict[str, Any]:
        info_dict_match = re.search(
            r"```json(.*?)```", content, re.DOTALL | re.MULTILINE
        )
        if info_dict_match is None:
            raise JSONObjectExtractionException(
                "The response does not contain the JSON object encapsulated by ```json```."
            )
        info_dict_str = info_dict_match.group(1)
        try:
            info_dict: dict[str, Any] = json.loads(info_dict_str)
        except Exception as e:
            raise JSONObjectExtractionException(
                "The JSON object in the response is invalid. It cannot be decoded."
            ) from e
        if required_key_list is None:
            return info_dict
        missing_key_list: list[str] = [
            key for key in required_key_list if key not in info_dict
        ]
        if missing_key_list:
            if len(missing_key_list) == 1:
                error_message = (
                    f"The JSON object in the response does not contain the following required key: "
                    f"`{missing_key_list[0]}`."
                )
            else:
                error_message = (
                    f"The JSON object in the response does not contain the following required keys: "
                    f"`{'`, `'.join(missing_key_list)}`."
                )
            raise JSONObjectExtractionException(error_message)
        return info_dict

    @staticmethod
    def get_single_chat_completion(
        client: OpenAI,
        model_name: str,
        message_list: Sequence[ChatCompletionMessageParam],
        token_usage_info_list_path: Optional[str] = None,
        log_prefix: Optional[str] = None,
    ) -> tuple[ChatCompletion, TokenUsageInfo]:
        log_prefix = log_prefix or ""
        try:
            chat_completion = client.chat.completions.create(
                model=model_name, messages=message_list, n=1
            )
        except Exception as e:
            SafeLogger.error(
                f"{log_prefix}Failed to send a request to the model {model_name}."
            )
            raise OpenaiCompletionException() from e
        SafeLogger.info(
            f"{log_prefix}Received a chat_completion from the model {model_name}."
        )
        if token_usage_info_list_path is None:
            token_usage_info = TokenUsageInfo.from_chat_completion(chat_completion)
        else:
            with ExclusiveJsonAccessUtility(
                token_usage_info_list_path
            ) as json_access_utility:
                token_usage_info = TokenUsageInfo.log_and_create_from_chat_completion(
                    chat_completion, json_access_utility
                )
        if chat_completion.choices[0].message.content is None:
            error_message = (
                f"{log_prefix}Cannot extract content from the chat_completion."
            )
            SafeLogger.error(error_message)
            raise OpenaiCompletionException(error_message)
        return chat_completion, token_usage_info


class ValidationStatus(StrEnum):
    VALID = "valid"
    CANNOT_BE_REUSED = "cannot_be_reused"
    CAN_BE_REUSED = "can_be_reused"
    REUSED = "reused"
    DUPLICATED_WITH_VALID_ENTRY = "duplicated_with_valid_entry"


class AllInOneEntry(BaseModel):
    validation_status: ValidationStatus
    target_skill_list: Sequence[str]

    @abstractmethod
    def get_skill_list(self) -> Optional[Sequence[str]]:
        pass

    @abstractmethod
    def get_action_list(self) -> Optional[Sequence[str]]:
        pass

    def __hash__(self) -> int:
        serialized = str(self.model_dump()).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return int(digest, 16)


AllInOneEntrySubclass = TypeVar("AllInOneEntrySubclass", bound=AllInOneEntry)
SkillUtilitySubclass = TypeVar("SkillUtilitySubclass", bound=SkillUtility)


class AllInOneFactory(ABC, Generic[AllInOneEntrySubclass]):
    def __init__(
        self,
        output_dir: str,
        logger_config: LoggerConfig,
        minimum_sample_count_per_skill: int,
        minimum_total_sample_count: int,
        maximum_consecutive_failure_count: int,
        model_name: str,
        enforce_deepseek_discount_flag: bool,
        entry_subclass_cls: type[AllInOneEntrySubclass],
        skill_utility_cls: type[SkillUtilitySubclass],
    ):
        os.makedirs(output_dir, exist_ok=True)
        # region Set valid_entry_list_path, invalid_entry_list_path, token_usage_info_list_path
        self.valid_entry_list_path = os.path.join(output_dir, "valid_entry_list.json")
        self.invalid_entry_list_path = os.path.join(
            output_dir, "invalid_entry_list.json"
        )
        self.token_usage_info_list_path = os.path.join(
            output_dir, "token_usage_info_list.json"
        )
        for path in [
            self.valid_entry_list_path,
            self.invalid_entry_list_path,
            self.token_usage_info_list_path,
        ]:
            with ExclusiveJsonAccessUtility(path) as json_access_utility:
                if not os.path.exists(path):
                    json_access_utility.write([])

        # endregion
        self.logger = SingletonLogger.get_instance(logger_config)
        # https://api.gptsapi.net/v1
        # https://api.deepseek.com/v1
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )
        self.minimum_sample_count_per_skill = minimum_sample_count_per_skill
        self.minimum_total_sample_count = minimum_total_sample_count
        self.maximum_consecutive_failure_count = maximum_consecutive_failure_count
        self.model_name = model_name
        self.enforce_deepseek_discount_flag = enforce_deepseek_discount_flag
        self.entry_subclass_cls = entry_subclass_cls
        self.skill_utility_cls = skill_utility_cls

    @abstractmethod
    def _get_skill_count_threshold(self, target_skill_count: int) -> int:
        pass

    @classmethod
    def _generate_candidate_skill_count_when_generating_target_skill_list(
        cls, insufficient_skill_count: int
    ) -> int:
        return random.randint(1, insufficient_skill_count)

    def _generate_target_skill_list(self) -> Optional[Sequence[str]]:
        # region Prepare
        with ExclusiveJsonAccessUtility(
            self.valid_entry_list_path
        ) as json_access_utility:
            generated_entry_list: Sequence[AllInOneEntrySubclass] = [
                self.entry_subclass_cls.model_validate(entry_dict)
                for entry_dict in json_access_utility.read()
            ]
        # endregion
        # region Find skills that have insufficient samples
        all_skill_list: Sequence[str] = self.skill_utility_cls.get_all_skill_list()
        skill_to_sample_count_dict: dict[str, int] = {
            skill: 0 for skill in all_skill_list
        }
        for entry in generated_entry_list:
            skill_list = entry.get_skill_list()
            assert skill_list is not None
            for skill in skill_list:
                skill_to_sample_count_dict[skill] += 1
        insufficient_skill_list: Sequence[str] = [
            skill
            for skill, sample_count in skill_to_sample_count_dict.items()
            if sample_count < self.minimum_sample_count_per_skill
        ]
        insufficient_skill_count = len(insufficient_skill_list)
        del insufficient_skill_list
        if insufficient_skill_count == 0:
            if len(generated_entry_list) > self.minimum_total_sample_count:
                return None
            else:
                insufficient_skill_count = len(all_skill_list)
        all_skill_weight = np.array(
            [1.0 / (skill_to_sample_count_dict[skill] + 1) for skill in all_skill_list],
            dtype=np.float64,
        )
        all_skill_weight = all_skill_weight / all_skill_weight.sum()
        # endregion
        # region Randomly select skills
        candidate_skill_count = (
            self._generate_candidate_skill_count_when_generating_target_skill_list(
                insufficient_skill_count
            )
        )
        candidate_skill_list: Sequence[str] = list(
            np.random.choice(
                all_skill_list,
                size=candidate_skill_count,
                replace=False,
                p=all_skill_weight,
            )
        )
        # endregion
        return candidate_skill_list

    def _is_duplicated_entry(
        self,
        entry: AllInOneEntrySubclass,
        valid_entry_list_json_access_utility: ExclusiveJsonAccessUtility,
    ) -> bool:
        # Check whether the action (or action list) is duplicated with valid entry
        action_list = entry.get_action_list()
        assert action_list is not None
        original_valid_entry_list: list[AllInOneEntrySubclass] = [
            self.entry_subclass_cls.model_validate(entry_dict)
            for entry_dict in valid_entry_list_json_access_utility.read()
        ]
        for existed_entry in original_valid_entry_list:
            existed_action_list = existed_entry.get_action_list()
            assert existed_action_list is not None
            if action_list == existed_action_list:
                return True
        return False

    def _reuse_entry(
        self,
        target_skill_list: Sequence[str],
        valid_entry_list_json_access_utility: ExclusiveJsonAccessUtility,
        invalid_entry_list_json_access_utility: ExclusiveJsonAccessUtility,
    ) -> Sequence[AllInOneEntrySubclass]:
        # region Move reused entries to new_buffered_entry_list
        original_buffered_entry_list: list[AllInOneEntrySubclass] = [
            self.entry_subclass_cls.model_validate(entry_dict)
            for entry_dict in invalid_entry_list_json_access_utility.read()
        ]
        reused_entry_list: list[AllInOneEntrySubclass] = []
        new_buffered_entry_list: list[AllInOneEntrySubclass] = []
        for entry in original_buffered_entry_list:
            skill_list = entry.get_skill_list()
            if skill_list is None:
                continue
            overlapped_skill_count = len(set(skill_list) & set(target_skill_list))
            if (
                overlapped_skill_count
                >= self._get_skill_count_threshold(len(target_skill_list))
                and entry.validation_status == ValidationStatus.CAN_BE_REUSED
            ):
                if self._is_duplicated_entry(
                    entry, valid_entry_list_json_access_utility
                ):
                    entry.validation_status = (
                        ValidationStatus.DUPLICATED_WITH_VALID_ENTRY
                    )
                    new_buffered_entry_list.append(entry)
                    continue
                entry.validation_status = ValidationStatus.REUSED
                entry.target_skill_list = target_skill_list
                reused_entry_list.append(entry)
            else:
                new_buffered_entry_list.append(entry)
        # endregion
        # region Write new_buffered_entry_list to invalid_entry_list
        invalid_entry_list_json_access_utility.write(
            [entry.model_dump() for entry in new_buffered_entry_list],
        )
        original_valid_entry_list = [
            self.entry_subclass_cls.model_validate(entry_dict)
            for entry_dict in valid_entry_list_json_access_utility.read()
        ]
        valid_entry_list_json_access_utility.write(
            [
                entry.model_dump()
                for entry in original_valid_entry_list + reused_entry_list
            ],
        )
        # endregion
        return reused_entry_list

    @abstractmethod
    def _generate_from_target_skill_list(
        self, target_skill_list: Sequence[str]
    ) -> AllInOneEntrySubclass:
        pass

    def construct(self) -> None:
        consecutive_failure_count = 0
        while consecutive_failure_count < self.maximum_consecutive_failure_count:
            # region Check DeepSeek discount
            if (
                not TokenUsageInfo.is_deepseek_discount_active(
                    int(datetime.datetime.now().timestamp())
                )
                and self.enforce_deepseek_discount_flag
            ):
                self.logger.error("Oh no! The DeepSeek discount is not active. Break.")
                break
            # endregion
            # region Find skills that have insufficient samples
            target_skill_list = self._generate_target_skill_list()
            self.logger.info(f"Get target_skill_list: {target_skill_list}")
            if target_skill_list is None:
                self.logger.info("All skills have sufficient samples. Break the loop.")
                break
            # endregion
            # region Reuse entries
            with ExclusiveJsonAccessUtility(
                self.valid_entry_list_path
            ) as valid_entry_list_json_access_utility:
                with ExclusiveJsonAccessUtility(
                    self.invalid_entry_list_path
                ) as invalid_entry_list_json_access_utility:
                    reused_entry_list = self._reuse_entry(
                        target_skill_list,
                        valid_entry_list_json_access_utility,
                        invalid_entry_list_json_access_utility,
                    )
                    if len(reused_entry_list) != 0:
                        consecutive_failure_count = 0
                        self.logger.info(
                            f"Reuse {len(reused_entry_list)} entries. Set consecutive_failure_count to 0."
                        )
                        continue
            # endregion
            # region Generate new entry
            try:
                generated_entry = self._generate_from_target_skill_list(
                    target_skill_list
                )
            except GenerationException as e:
                self.logger.error(str(e))
                consecutive_failure_count += 1
                continue
            # endregion
            # region Write new entry
            # region Write valid entry
            if generated_entry.validation_status == ValidationStatus.VALID:
                with ExclusiveJsonAccessUtility(
                    self.valid_entry_list_path
                ) as json_access_utility:
                    original_valid_entry_list: list[AllInOneEntry] = [
                        self.entry_subclass_cls.model_validate(entry_dict)
                        for entry_dict in json_access_utility.read()
                    ]
                    if self._is_duplicated_entry(generated_entry, json_access_utility):
                        generated_entry.validation_status = (
                            ValidationStatus.DUPLICATED_WITH_VALID_ENTRY
                        )
                        self.logger.error(
                            f"Generated entry is duplicated with valid entry. "
                            f"Set validation_status to {generated_entry.validation_status}. "
                            f"Current valid_entry_list length: {len(original_valid_entry_list)}."
                        )
                    else:
                        json_access_utility.write(
                            [
                                entry.model_dump()
                                for entry in original_valid_entry_list
                                + [generated_entry]
                            ]
                        )
                        self.logger.info(
                            f"Generate a valid entry."
                            f"Current valid_entry_list length: {len(original_valid_entry_list) + 1}."
                        )
            else:
                self.logger.error(
                    f"Failed to generate a valid entry. "
                    f"Consecutive failure count: {consecutive_failure_count}."
                )
            # endregion
            # region Write invalid entry, maintain consecutive_failure_count
            if generated_entry.validation_status != ValidationStatus.VALID:
                consecutive_failure_count += 1
                with ExclusiveJsonAccessUtility(
                    self.invalid_entry_list_path
                ) as json_access_utility:
                    original_invalid_entry_list: list[AllInOneEntrySubclass] = [
                        self.entry_subclass_cls.model_validate(entry_dict)
                        for entry_dict in json_access_utility.read()
                    ]
                    new_invalid_entry_list: Sequence[AllInOneEntrySubclass] = (
                        original_invalid_entry_list + [generated_entry]
                    )
                    json_access_utility.write(
                        [
                            entry_dict.model_dump()
                            for entry_dict in new_invalid_entry_list
                        ],
                    )
                    self.logger.info(
                        f"Current invalid_entry_list length: {len(new_invalid_entry_list)}"
                    )
            else:
                consecutive_failure_count = 0
                self.logger.info(
                    f"Generated entry is valid. Set consecutive_failure_count to 0."
                )
            # endregion
            # endregion


class DatasetInfo(BaseModel):
    raw_entry_path: str
    raw_entry_length: int
    sample_count: int
    random_seed: int
    output_dir: str
    created_time: str
    index_dict: Mapping[int, int]  # current_index -> original_index


class ProcessedEntryFactory(ABC, Generic[AllInOneEntrySubclass]):
    def __init__(
        self,
        raw_entry_path: str,
        output_dir: str,
        log_file_path: str,
        random_seed: int,
        raw_entry_cls: type[AllInOneEntrySubclass],
    ):
        self.raw_entry_path = raw_entry_path
        self.output_dir = output_dir
        self.random_seed = random_seed
        logger_config = LoggerConfig(
            level="INFO",
            log_file_path=log_file_path,
            logger_name="db_bench_standard_data_factory",
        )
        self.logger = SingletonLogger.get_instance(logger_config)
        self.raw_entry_cls = raw_entry_cls

    def _get_output_path_dict(self) -> Mapping[str, str]:
        entry_dict_output_path = os.path.join(self.output_dir, "entry_dict.json")
        dataset_info_output_path = os.path.join(self.output_dir, "dataset_info.json")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        return {
            "entry_dict_output_path": entry_dict_output_path,
            "dataset_info_output_path": dataset_info_output_path,
        }

    @abstractmethod
    def _construct_processed_entry_from_raw_entry(
        self, raw_entry: AllInOneEntrySubclass
    ) -> Mapping[str, Any]:
        pass

    def random_order_construct(self, sample_count: Optional[int] = None) -> None:
        # region Prepare
        random.seed(self.random_seed)
        raw_entry_list: Sequence[AllInOneEntrySubclass] = [
            self.raw_entry_cls.model_validate(entry_dict)
            for entry_dict in json.load(open(self.raw_entry_path, "r"))
        ]
        if sample_count is None:
            sample_count = len(raw_entry_list)
        assert 0 < sample_count <= len(raw_entry_list)
        # endregion
        # region Construct processed_entry_list, raw_entry_hash_to_index_dict
        processed_entry_list: list[Mapping[str, Any]] = []
        raw_entry_hash_to_index_dict: dict[int, int] = {}
        for (
            raw_entry_index,
            raw_entry,
        ) in enumerate(raw_entry_list):
            processed_entry = self._construct_processed_entry_from_raw_entry(raw_entry)
            assert "raw_entry_hash" not in processed_entry
            raw_entry_hash = hash(raw_entry)
            raw_entry_hash_to_index_dict[raw_entry_hash] = raw_entry_index
            processed_entry_list.append(
                {
                    **processed_entry,
                    "raw_entry_hash": raw_entry_hash,
                }
            )
        # endregion
        # region Shuffle processed_entry_list
        random.shuffle(processed_entry_list)
        processed_entry_list = processed_entry_list[:sample_count]
        index_dict: dict[int, int] = {}
        for processed_entry_index, processed_entry in enumerate(processed_entry_list):
            raw_entry_index = raw_entry_hash_to_index_dict[
                processed_entry["raw_entry_hash"]
            ]
            index_dict[processed_entry_index] = raw_entry_index
        # endregion
        # region Construct dataset_info
        dataset_info = DatasetInfo(
            raw_entry_path=self.raw_entry_path,
            raw_entry_length=len(raw_entry_list),
            sample_count=sample_count,
            random_seed=self.random_seed,
            output_dir=self.output_dir,
            created_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            index_dict=index_dict,
        )
        # endregion
        # region Dump processed_entry_list and dataset_info
        output_path_dict = self._get_output_path_dict()
        json.dump(
            {
                str(entry_index): entry
                for entry_index, entry in enumerate(processed_entry_list)
            },
            open(output_path_dict["entry_dict_output_path"], "w"),  # noqa
            indent=2,
        )
        json.dump(
            dataset_info.model_dump(),
            open(output_path_dict["dataset_info_output_path"], "w"),  # noqa
            indent=2,
        )
        # endregion

    @abstractmethod
    def validate(self) -> None:
        pass
