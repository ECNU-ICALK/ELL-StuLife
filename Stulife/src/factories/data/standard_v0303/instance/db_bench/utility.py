from typing import Sequence, TypeVar, Optional, final, Generic
from pydantic import BaseModel
import os
from abc import abstractmethod, ABC
import threading
from openai import OpenAI
import datetime

from src.factories.data.standard_v0303.utility import (
    ExclusiveJsonAccessUtility,
    OpenaiCompletionException,
    TokenUsageInfo,
)
from src.utils import SingletonLogger
from src.typings import LoggerConfig


class DBBenchGenerationException(Exception):
    pass


Entry = TypeVar("Entry", bound=BaseModel)
LowLevelEntry = TypeVar("LowLevelEntry", bound=BaseModel)
HighLevelEntry = TypeVar("HighLevelEntry", bound=BaseModel)
CurrentLevelEntry = TypeVar("CurrentLevelEntry", bound=BaseModel)


class GenerationArgument(BaseModel, Generic[Entry]):
    low_level_entry: Entry
    model_name: str


class GenerationResult(BaseModel, Generic[Entry]):
    current_level_entry: Entry
    success_flag: bool


class DBBenchDataFactory(ABC, Generic[LowLevelEntry, CurrentLevelEntry]):
    unprocessed_low_level_entry_list_initialization_barrier: Optional[
        threading.Barrier
    ] = None

    def __init__(
        self,
        valid_low_level_entry_output_path: str,
        output_dir: str,
        log_file_path: str,
        model_name_list: Sequence[str],
        maximum_consecutive_failure_count: int,
        enforce_deepseek_discount_flag: bool,
        low_level_entry_cls: type[LowLevelEntry],
        current_level_entry_cls: type[CurrentLevelEntry],
    ) -> None:
        # region Set low_level_entry_cls and current_level_entry_cls
        self.low_level_entry_cls = low_level_entry_cls
        self.current_level_entry_cls = current_level_entry_cls
        # endregion
        # region Set logger
        logger_config = LoggerConfig(
            level="INFO",
            log_file_path=log_file_path,
            logger_name="db_bench_standard_data_factory",
        )
        self.logger = SingletonLogger.get_instance(logger_config)
        # endregion
        # region Create output_dir if it does not exist
        os.makedirs(output_dir, exist_ok=True)
        # endregion
        # region Get valid_low_level_entry_output_path
        self.valid_low_level_entry_output_path = valid_low_level_entry_output_path
        # endregion
        # region Set valid_current_level_entry_list_path
        self.valid_current_level_entry_list_path = (
            self.get_valid_current_level_entry_list_path(output_dir)
        )
        with ExclusiveJsonAccessUtility(
            self.valid_current_level_entry_list_path
        ) as json_access_utility:
            if not os.path.exists(self.valid_current_level_entry_list_path):
                json_access_utility.write([])
        # endregion
        # region Set invalid_current_level_entry_list_path
        self.invalid_current_level_entry_list_path = os.path.join(
            output_dir, "invalid_current_level_entry_list.json"
        )
        with ExclusiveJsonAccessUtility(
            self.invalid_current_level_entry_list_path
        ) as json_access_utility:
            if not os.path.exists(self.invalid_current_level_entry_list_path):
                json_access_utility.write([])
        # endregion
        # region Set unprocessed_low_level_entry_list_path
        self.unprocessed_low_level_entry_list_path = os.path.join(
            output_dir, "unprocessed_low_level_entry_list.json"
        )
        self._initialize_unprocessed_low_level_entry_list()
        if self.unprocessed_low_level_entry_list_initialization_barrier is not None:
            self.unprocessed_low_level_entry_list_initialization_barrier.wait()
        # endregion
        # region Set token_usage_info_list_path
        self.token_usage_info_list_path = os.path.join(
            output_dir, "token_usage_info_list.json"
        )
        with ExclusiveJsonAccessUtility(
            self.token_usage_info_list_path
        ) as json_access_utility:
            if not os.path.exists(self.token_usage_info_list_path):
                json_access_utility.write([])
        # endregion
        self.maximum_consecutive_failure_count = maximum_consecutive_failure_count
        self.enforce_deepseek_discount_flag = enforce_deepseek_discount_flag
        self.model_name_list = model_name_list
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )

    @final
    def _initialize_unprocessed_low_level_entry_list(self) -> None:
        with ExclusiveJsonAccessUtility(
            self.valid_low_level_entry_output_path
        ) as valid_low_level_entry_list_json_access_utility:
            with ExclusiveJsonAccessUtility(
                self.valid_current_level_entry_list_path
            ) as valid_current_level_entry_list_json_access_utility:
                with ExclusiveJsonAccessUtility(
                    self.invalid_current_level_entry_list_path
                ) as invalid_current_level_entry_list_json_access_utility:
                    with ExclusiveJsonAccessUtility(
                        self.unprocessed_low_level_entry_list_path
                    ) as unprocessed_low_level_entry_list_json_access_utility:
                        # region Construct entry_set
                        processed_valid_low_level_entry_list: Sequence[
                            LowLevelEntry
                        ] = [
                            self._extract_low_level_entry_from_current_level_entry(
                                self.current_level_entry_cls.model_validate(
                                    current_level_entry_dict
                                )
                            )
                            for current_level_entry_dict in valid_current_level_entry_list_json_access_utility.read()
                        ]
                        processed_invalid_low_level_entry_list: Sequence[
                            LowLevelEntry
                        ] = [
                            self._extract_low_level_entry_from_current_level_entry(
                                self.current_level_entry_cls.model_validate(
                                    current_level_entry_dict
                                )
                            )
                            for current_level_entry_dict in invalid_current_level_entry_list_json_access_utility.read()
                        ]
                        processed_valid_low_level_entry_set: set[LowLevelEntry] = set(
                            processed_valid_low_level_entry_list
                        )
                        processed_invalid_low_level_entry_set: set[LowLevelEntry] = set(
                            processed_invalid_low_level_entry_list
                        )
                        # endregion
                        # region Move unprocessed_low_level_entry to unprocessed_low_level_entry_list
                        merged_processed_low_level_entry_set = (
                            processed_valid_low_level_entry_set
                            | processed_invalid_low_level_entry_set
                        )
                        valid_low_level_entry_list: Sequence[LowLevelEntry] = [
                            self.low_level_entry_cls.model_validate(
                                low_level_entry_dict
                            )
                            for low_level_entry_dict in valid_low_level_entry_list_json_access_utility.read()
                        ]
                        unprocessed_low_level_entry_list: list[LowLevelEntry] = []
                        for low_level_entry in valid_low_level_entry_list:
                            if (
                                low_level_entry
                                not in merged_processed_low_level_entry_set
                            ):
                                unprocessed_low_level_entry_list.append(low_level_entry)
                        # endregion
                        # region Write result
                        unprocessed_low_level_entry_list_json_access_utility.write(
                            [
                                low_level_entry_dict.model_dump()
                                for low_level_entry_dict in unprocessed_low_level_entry_list
                            ]
                        )
                        # endregion

    @staticmethod
    @abstractmethod
    def _extract_low_level_entry_from_current_level_entry(
        current_level_entry: CurrentLevelEntry,
    ) -> LowLevelEntry:
        pass

    @staticmethod
    @final
    def get_valid_current_level_entry_list_path(output_dir: str) -> str:
        return os.path.join(output_dir, "valid_current_level_entry_list.json")

    @final
    def _get_unprocessed_low_level_entry(self) -> Optional[LowLevelEntry]:
        with ExclusiveJsonAccessUtility(
            self.unprocessed_low_level_entry_list_path
        ) as json_access_utility:
            unprocessed_low_level_entry_list: list[LowLevelEntry] = [
                self.low_level_entry_cls.model_validate(low_level_entry_dict)
                for low_level_entry_dict in json_access_utility.read()
            ]
            if len(unprocessed_low_level_entry_list) == 0:
                return None
            low_level_entry = unprocessed_low_level_entry_list.pop(0)
            json_access_utility.write(
                [
                    low_level_entry.model_dump()
                    for low_level_entry in unprocessed_low_level_entry_list
                ]
            )
        return low_level_entry

    @abstractmethod
    def _generate_from_low_level_entry(
        self,
        generation_argument: GenerationArgument[LowLevelEntry],
    ) -> GenerationResult[CurrentLevelEntry]:
        pass

    @final
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
            # region Get a low_level_entry
            unprocessed_low_level_entry = self._get_unprocessed_low_level_entry()
            if unprocessed_low_level_entry is None:
                self.logger.info("No more unprocessed low level entry.")
                break
            self.logger.info(
                f"Get an unprocessed low_level_entry: {unprocessed_low_level_entry}"
            )
            # endregion
            # region Generate current_level_entry
            invalid_current_level_entry_list: list[CurrentLevelEntry] = []
            valid_current_level_entry: Optional[CurrentLevelEntry] = None
            for model_name in self.model_name_list:
                self.logger.info(
                    f"Start generating instruction using model {model_name}."
                )
                try:
                    generation_result: GenerationResult[CurrentLevelEntry] = (
                        self._generate_from_low_level_entry(
                            GenerationArgument(
                                low_level_entry=unprocessed_low_level_entry,
                                model_name=model_name,
                            )
                        )
                    )
                except (OpenaiCompletionException, DBBenchGenerationException) as e:
                    self.logger.error(str(e))
                    continue
                if generation_result.success_flag:
                    valid_current_level_entry = generation_result.current_level_entry
                    break
                else:
                    invalid_current_level_entry_list.append(
                        generation_result.current_level_entry
                    )
            # endregion
            # region Handle the result
            # region Only write valid_current_level_entry if it not None. Maintain consecutive_failure_count
            if valid_current_level_entry is None:
                # This block will be executed if
                #   1. Cannot generate from low_leve_entry
                #   2. Error arises from OpenAI API
                consecutive_failure_count += 1
                self.logger.error(
                    f"Cannot generate from low_leve_entry. "
                    f"Consecutive failure count: {consecutive_failure_count}"
                )
            else:
                consecutive_failure_count = 0  # Reset the consecutive_failure_count
                # region Write valid_current_level_entry
                with ExclusiveJsonAccessUtility(
                    self.valid_current_level_entry_list_path
                ) as json_access_utility:
                    original_valid_current_level_entry_list: list[CurrentLevelEntry] = [
                        self.current_level_entry_cls.model_validate(
                            current_level_entry_dict
                        )
                        for current_level_entry_dict in json_access_utility.read()
                    ]
                    new_valid_current_level_entry_list: list[CurrentLevelEntry] = (
                        original_valid_current_level_entry_list
                        + [valid_current_level_entry]
                    )
                    json_access_utility.write(
                        [
                            current_level_entry.model_dump()
                            for current_level_entry in new_valid_current_level_entry_list
                        ]
                    )
                    self.logger.info(
                        f"Current valid_current_level_entry_list length: "
                        f"{len(new_valid_current_level_entry_list)}"
                    )
            # endregion
            # region Always write invalid_current_level_entry_list
            with ExclusiveJsonAccessUtility(
                self.invalid_current_level_entry_list_path
            ) as json_access_utility:
                original_invalid_current_level_entry_list: list[CurrentLevelEntry] = [
                    self.current_level_entry_cls.model_validate(
                        current_level_entry_dict
                    )
                    for current_level_entry_dict in json_access_utility.read()
                ]
                new_invalid_current_level_entry_list: list[CurrentLevelEntry] = (
                    original_invalid_current_level_entry_list
                    + invalid_current_level_entry_list
                )
                json_access_utility.write(
                    [
                        current_level_entry.model_dump()
                        for current_level_entry in new_invalid_current_level_entry_list
                    ]
                )
                self.logger.info(
                    f"Current invalid_current_level_entry_list length: {len(new_invalid_current_level_entry_list)}"
                )
            # endregion
            # region Maintain unprocessed_low_level_entry_list
            # If not value are recorded in both valid_current_level_entry and invalid_current_level_entry_list,
            #   the SQL entry will be added back to unprocessed_low_level_entry_list.
            if (
                valid_current_level_entry is None
                and len(invalid_current_level_entry_list) == 0
            ):
                with ExclusiveJsonAccessUtility(
                    self.unprocessed_low_level_entry_list_path
                ) as json_access_utility:
                    unprocessed_low_level_entry_list: list[LowLevelEntry] = [
                        self.low_level_entry_cls.model_validate(low_level_entry_dict)
                        for low_level_entry_dict in json_access_utility.read()
                    ]
                    unprocessed_low_level_entry_list = [
                        unprocessed_low_level_entry
                    ] + unprocessed_low_level_entry_list
                    json_access_utility.write(
                        [
                            low_level_entry.model_dump()
                            for low_level_entry in unprocessed_low_level_entry_list
                        ]
                    )
            # endregion
            # endregion
