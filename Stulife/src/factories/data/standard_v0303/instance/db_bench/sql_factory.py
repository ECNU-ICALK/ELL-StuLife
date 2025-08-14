from enum import StrEnum
from openai.types.chat import ChatCompletionMessageParam
from openai import OpenAI
import os
import json
from typing import Optional, Sequence, Mapping, Self
from pydantic import BaseModel, model_validator
import random
import re
import sqlglot
import datetime
import concurrent.futures
import numpy as np
import hashlib
import threading
import time
from decimal import Decimal

from src.tasks.instance.db_bench.container import DBBenchContainer
from src.tasks.instance.db_bench.task import (
    DBBenchType,
    ColumnInfo,
    TableInfo,
    DBBench,
    DBBenchSkillUtility,
    AnswerType,
)
from src.factories.data.standard_v0303.instance.db_bench.demonstration import (
    SQL_FACTORY_DEMONSTRATION_INFO_DICT,
)
from src.factories.data.standard_v0303.instance.db_bench.skill_evaluator import (
    SkillEvaluator,
)
from src.utils import SingletonLogger, SafeLogger
from src.typings import LoggerConfig
from src.factories.data.standard_v0303.utility import (
    TokenUsageInfo,
    ExclusiveJsonAccessUtility,
    OpenaiCompletionException,
    JSONObjectExtractionException,
    DataFactoryUtility,
)


class SQLEntryValidationStatus(StrEnum):
    VALID = "valid"
    CANNOT_BE_REUSED = "cannot_be_reused"
    CAN_BE_REUSED = "can_be_reused"
    REUSED = "reused"


class SQLGenerationInfo(BaseModel):
    sql: str
    column_info_list: Sequence[ColumnInfo]
    table_name: str
    skill_list: Optional[Sequence[str]] = None
    invalid_reason: Optional[str] = None


class SQLValidationResult(BaseModel):
    generation_info: SQLGenerationInfo
    validation_status: SQLEntryValidationStatus


class SQLEntry(BaseModel):
    generation_info_list: Sequence[SQLGenerationInfo]
    validation_status: SQLEntryValidationStatus
    target_skill_list: Sequence[str]
    scenario: str
    token_usage_info_list: Sequence[TokenUsageInfo]

    def __hash__(self) -> int:
        serialized = str(self.model_dump()).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return int(digest, 16)


class PseudoDBBenchAnswerInfo(BaseModel):
    answer_type: AnswerType


class PseudoDBBenchDatasetItem(BaseModel):
    table_info: TableInfo
    database_name: str
    answer_info: PseudoDBBenchAnswerInfo


class SQLExecutionResult(BaseModel):
    answer_direct: Optional[DBBenchType.AnswerDirect] = None
    original_table_md5: Optional[str] = None
    executed_sql_table_md5: Optional[str] = None

    @model_validator(mode="after")
    def validate_field(self) -> Self:
        if self.answer_direct is None:
            assert self.original_table_md5 is not None
            assert self.executed_sql_table_md5 is not None
        else:
            assert self.answer_direct is not None
        return self


class PseudoDBBench:
    _lock: threading.Lock = threading.Lock()

    def __init__(self, sql_execution_interval: int) -> None:
        self.container = DBBenchContainer()
        self.current_dataset_item: Optional[PseudoDBBenchDatasetItem] = None
        self.sql_execution_interval = sql_execution_interval

    def _get_current_dataset_item(self) -> PseudoDBBenchDatasetItem:
        assert self.current_dataset_item is not None  # Type narrowing
        return self.current_dataset_item

    def execute_sql(
        self,
        sql: str,
        table_name: str,
        column_info_list: Sequence[ColumnInfo],
        row_list: Sequence[DBBenchType.Row],
    ) -> SQLExecutionResult:
        """
        The function will also initialize the database, and clean up the database after the execution of the SQL query.
        The error that happens during the execution of the SQL query will be raised to the caller.
        """
        with PseudoDBBench._lock:
            # region Init database
            # region Set self.current_dataset_item
            table_info = TableInfo(
                name=table_name,
                row_list=row_list,
                column_info_list=column_info_list,
            )
            # https://github.com/caixd-220529/continual_agent_bench/blob/726f5d07b03e52aff79098133bc8385ba4e8c396/src/tasks/instance/db_bench/task.py#L349
            # `database_name` is the same as `table_name`. It will also be used to clean up the database.
            database_name = table_name
            answer_type: AnswerType
            if sql.upper().startswith("SELECT"):
                answer_type = AnswerType.DIRECT
            else:
                answer_type = AnswerType.MD5
            pseudo_db_bench_dataset_item = PseudoDBBenchDatasetItem(
                table_info=table_info,
                database_name=table_info.name,
                answer_info=PseudoDBBenchAnswerInfo(answer_type=answer_type),
            )
            self.current_dataset_item = pseudo_db_bench_dataset_item
            # endregion
            init_sql = DBBench._build_init_sql(pseudo_db_bench_dataset_item)  # type: ignore[arg-type]  # noqa
            self.container.execute(init_sql)
            SafeLogger.info(
                f"Initiated database: {pseudo_db_bench_dataset_item.database_name}."
            )
            time.sleep(self.sql_execution_interval)
            # endregion
            # region If the SQL is not a SELECT query, get original_table_md5
            original_table_md5: Optional[str] = None
            if not sql.startswith("SELECT"):
                original_table_md5 = DBBench._get_task_output(  # noqa
                    self, ""  # type: ignore[arg-type]
                )["answer"]
                SafeLogger.info(f"Extracted original table MD5: {original_table_md5}.")
                time.sleep(self.sql_execution_interval)
            # endregion
            # region Execute SQL
            self.container.conn.reconnect()
            cursor = self.container.conn.cursor()
            cursor.execute(f"use `{pseudo_db_bench_dataset_item.database_name}`")
            cursor.fetchall()
            cursor.execute(sql)
            structured_sql_output = cursor.fetchall()
            self.container.conn.commit()
            time.sleep(self.sql_execution_interval)
            # endregion
            # region Set SQLExecutionResult values
            sql_execution_result: SQLExecutionResult
            if sql.startswith("SELECT"):
                # region Convert Decimal to float
                ground_truth_direct: list[DBBenchType.Row] = []
                for row_index, raw_row_tuple in enumerate(structured_sql_output):
                    processed_row_list = []
                    for value in raw_row_tuple:
                        if isinstance(value, Decimal):
                            value = float(value)
                        processed_row_list.append(value)
                    ground_truth_direct.append(tuple(processed_row_list))
                SafeLogger.info(
                    f"Extracted the SELECT result: {len(ground_truth_direct)=}."
                )
                # endregion
                sql_execution_result = SQLExecutionResult(
                    answer_direct=ground_truth_direct,
                )
            else:
                # region Get executed_sql_table_md5
                executed_sql_table_md5 = DBBench._get_task_output(  # noqa
                    self, ""  # type: ignore[arg-type]
                )["answer"]
                time.sleep(self.sql_execution_interval)
                SafeLogger.info(
                    f"Extracted executed SQL table MD5: {executed_sql_table_md5}."
                )
                # endregion
                sql_execution_result = SQLExecutionResult(
                    original_table_md5=original_table_md5,
                    executed_sql_table_md5=executed_sql_table_md5,
                )
            # endregion
            # region Clean up
            self.container.execute(f"drop database `{database_name}`")  # noqa
            time.sleep(self.sql_execution_interval)
            # endregion
            return sql_execution_result


class SQLFactory:
    _pseudo_db_bench_lock: threading.Lock = threading.Lock()
    _pseudo_db_bench: Optional[PseudoDBBench] = None

    def __init__(
        self,
        output_dir: str,
        minimum_sample_count_per_skill: int,
        minimum_total_sample_count: int,
        log_file_path: str,
        generation_attempt_count_per_target_skill_list: int,
        maximum_consecutive_failure_count: int,
        model_name_list: list[str],
        enforce_deepseek_discount_flag: bool,
    ):
        os.makedirs(output_dir, exist_ok=True)
        # region Set valid_sql_entry_list_path
        self.valid_sql_entry_list_path = SQLFactory.get_valid_sql_entry_list_path(
            output_dir
        )
        with ExclusiveJsonAccessUtility(
            self.valid_sql_entry_list_path
        ) as json_access_utility:
            if not os.path.exists(self.valid_sql_entry_list_path):
                json_access_utility.write([])
        # endregion
        # region Set invalid_sql_entry_list_path
        self.invalid_sql_entry_list_path = os.path.join(
            output_dir, "invalid_sql_entry_list.json"
        )
        with ExclusiveJsonAccessUtility(
            self.invalid_sql_entry_list_path
        ) as json_access_utility:
            if not os.path.exists(self.invalid_sql_entry_list_path):
                json_access_utility.write([])
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
        # region Set table_name_info_dict_path
        self.table_name_info_dict_path = os.path.join(
            output_dir, "table_name_info_dict.json"
        )  # scenario -> table_name -> count
        with ExclusiveJsonAccessUtility(
            self.table_name_info_dict_path
        ) as json_access_utility:
            if not os.path.exists(self.table_name_info_dict_path):
                json_access_utility.write({})
        # endregion
        self.minimum_total_sample_count = minimum_total_sample_count
        self.minimum_sample_count_per_skill = minimum_sample_count_per_skill
        self.scenario_list = [
            "school",
            "hospital",
            "bank",
            "supermarket",
            "library",
            "hotel",
            "airport",
            "university",
            "train_station",
            "cinema",
            "warehouse",
            "restaurant",
            "company",
            "retail_store",
            "online_marketplace",
            "automotive_dealership",
            "fitness_center",
            "pharmacy",
            "government_office",
            "tech_startup",
            "e_commerce",
            "logistics",
            "real_estate",
            "manufacturing",
            "insurance",
            "telecommunications",
            "tourism",
            "media_outlet",
            "event_management",
            "veterinary_clinic",
            "travel_agency",
            "construction_site",
            "sports_arena",
            "music_venue",
            "art_gallery",
            "research_lab",
            "stadium",
            "theater",
            "car_rental",
        ]
        logger_config = LoggerConfig(
            level="INFO",
            log_file_path=log_file_path,
            logger_name="db_bench_standard_data_factory",
        )
        self.logger = SingletonLogger.get_instance(logger_config)
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )
        # https://api.gptsapi.net/v1
        # https://api.deepseek.com/v1
        self.generation_attempt_count_per_target_skill_list = (
            generation_attempt_count_per_target_skill_list
        )
        self.maximum_consecutive_failure_count = maximum_consecutive_failure_count
        self.model_name_list = model_name_list
        self.enforce_deepseek_discount_flag = enforce_deepseek_discount_flag
        assert self._pseudo_db_bench is not None

    @staticmethod
    def get_valid_sql_entry_list_path(output_dir: str) -> str:
        return os.path.join(output_dir, "valid_sql_entry_list.json")

    @staticmethod
    def _get_skill_count_threshold(target_skill_count: int) -> int:
        # The upper bound is chosen randomly. Maybe there will be a better choice.
        result = min(4, (target_skill_count * 1) // 2)
        if result == 0:
            return 1
        else:
            return result

    @classmethod
    def set_pseudo_db_bench(cls, pseudo_db_bench: PseudoDBBench) -> None:
        cls._pseudo_db_bench = pseudo_db_bench

    def _generate_target_skill_list(self) -> Sequence[str]:
        # region Prepare
        with ExclusiveJsonAccessUtility(
            self.valid_sql_entry_list_path
        ) as json_access_utility:
            generated_sql_entry_list: Sequence[SQLEntry] = [
                SQLEntry.model_validate(sql_entry_dict)
                for sql_entry_dict in json_access_utility.read()
            ]
        # endregion
        # region Find skills that have insufficient samples
        all_skill_list: Sequence[str] = DBBenchSkillUtility.get_all_skill_list()
        skill_count_dict: dict[str, int] = {skill: 0 for skill in all_skill_list}
        for sql_entry in generated_sql_entry_list:
            skill_list = sql_entry.generation_info_list[-1].skill_list
            assert skill_list is not None
            for skill in skill_list:
                skill_count_dict[skill] += 1
        insufficient_skill_list: Sequence[str] = [
            skill
            for skill in skill_count_dict
            if skill_count_dict[skill] < self.minimum_sample_count_per_skill
        ]  # List of skills that have insufficient samples
        insufficient_skill_count = len(insufficient_skill_list)
        if insufficient_skill_count == 0:
            if len(generated_sql_entry_list) > self.minimum_total_sample_count:
                return []
            else:
                insufficient_skill_count = len(all_skill_list)
        all_skill_weight = np.array(
            [1.0 / (skill_count_dict[skill] + 1) for skill in all_skill_list],
            dtype=np.float64,
        )
        all_skill_weight = all_skill_weight / np.sum(all_skill_weight)
        # endregion
        # region Randomly select skills
        candidate_skill_count = random.randint(1, insufficient_skill_count)
        candidate_skill_list: Sequence[str] = list(
            np.random.choice(
                all_skill_list,
                size=candidate_skill_count,
                replace=False,
                p=all_skill_weight,
            )
        )
        # endregion
        # region Skills with the same pattern are usually contradicted to each other
        target_skill_list: list[str] = []
        suffix_set: set[str] = set()
        for skill in candidate_skill_list:
            suffix = skill[:5]
            if suffix not in suffix_set:
                target_skill_list.append(skill)
            suffix_set.add(suffix)
        # endregion
        return target_skill_list

    @staticmethod
    def _construct_prompt(
        target_skill_list: Sequence[str],
        scenario: str,
        frequent_table_name_list: Optional[Sequence[str]],
    ) -> str:
        # region Construct demonstration_str
        demonstration_str = ""
        for skill_index, skill in enumerate(target_skill_list):
            single_skill_demonstration_str = f"""Skill {skill_index + 1}: {skill}
Explanation: {SQL_FACTORY_DEMONSTRATION_INFO_DICT[skill]["explanation"]}
Demonstration:
"""
            for demonstration in SQL_FACTORY_DEMONSTRATION_INFO_DICT[skill][
                "demonstration"
            ]:
                assert isinstance(demonstration, Mapping)
                single_skill_demonstration_str += f"- {demonstration['sql']}\n"
            single_skill_demonstration_str += "\n"
            demonstration_str += single_skill_demonstration_str
        # Remove the last two newline characters
        demonstration_str = demonstration_str[:-2]
        # endregion
        # region Construct frequent_table_name_str
        if frequent_table_name_list is not None:
            frequent_table_name_str = (
                " In this scenario, the following table names have been used frequently: "
                + ", ".join(frequent_table_name_list)
                + f'. Generate an alternative table name that refers to other areas within scenario "{scenario}".'
            )
        else:
            frequent_table_name_str = ""
        # endregion
        # region Write prompt
        prompt = f"""I am building a dataset for a database benchmarking task using SQL queries. Every SQL query in this dataset is labeled with one or more skills.

Your task is to generate one SQL query along with supplementary information. Please follow these guidelines:

1. Output Format:
    - The response must contain a JSON object encapsulated within a ```json``` code block.
    - The JSON object must include three keys:
        - table_name (str): The table's name.
        - sql (str): The single-line SQL query ending with a semicolon.
        - column_info_list (list[dict[str, str]]): A list of dictionaries with:
            - name (str): The column name.
            - type (str): Column type, which must be either INT or TEXT.

2. Basic Requirements:
    - The SQL query should relate to only one table.
    - Table and column names must include only letters, numbers, underscores, or hyphens (no other special characters or spaces). Do not include other special characters in the names, such as double quotation marks, single quotation marks, brackets, comma, period, etc.
    - Define around 4–7 columns in the table. (Not all columns need to appear in the SQL query; any omitted columns should be included in column_info_list.)
    - Every derived table must have its own alias.
    - Prefer SELECT statements with explicit column names over SELECT *.
    - There is no need to include the skills applied in the SQL query within the JSON object. 
    - You do not need to fill the value of the database. The value in the database will not contain double quotation marks (""), single quotation marks ('), brackets (()), comma (,), backquote(`), and backslash (\). There will not be NULL values in the database.
    - The SQL query should efficiently retrieves or modifies the required data while avoiding unnecessary complexity. Ensure that the query does not include redundant subqueries, unnecessary ordering, or excessive nesting. Always strive for the simplest. Before submitting your SQL query in the JSON object, you need to review and simplify it to eliminate redundant operations.
    - The available skills are strictly limited to {sorted(target_skill_list)}. Do not generate a SQL query that requires skills beyond those provided.
    - The query should relate to the scenario "{scenario}".{frequent_table_name_str}
 
   
3. The generated SQL query should be associated with the following skills. Note that some skills may conflict, so you do not need to associate all skills. About {SQLFactory._get_skill_count_threshold(len(target_skill_list))} of them should be asscodiated to the SQL query. I prefer an SQL query that is simple and concise.

4. Here is that required skills that need to be included in the SQL query: {sorted(target_skill_list)}.
Below are demonstration examples for the required skills:
{demonstration_str}

Generate your answer based on these instructions.
"""
        # endregion
        return prompt

    @staticmethod
    def _is_valid_string(string: str) -> bool:
        if re.match(r"^[a-zA-Z0-9_-]*$", string) is None:
            return False
        return True

    @classmethod
    def _validate_sql(
        cls,
        target_skill_list: Sequence[str],
        sql: str,
        table_name: str,
        column_info_list: Sequence[ColumnInfo],
    ) -> SQLValidationResult:
        def construct_complete_invalid_reason(_invalid_reason_list: list[str]) -> str:
            _result = "Invalid reason:\n"
            for _invalid_reason in _invalid_reason_list:
                _result += f"- {_invalid_reason}\n"
            return _result

        # region Validate table_name and the name of columns
        # Leave sql_entry.skill_list to be None
        invalid_reason_list: list[str] = []
        if not SQLFactory._is_valid_string(table_name):
            invalid_reason = f"Invalid table_name: {table_name}."
            invalid_reason_list.append(invalid_reason)
        for column_info in column_info_list:
            if not SQLFactory._is_valid_string(column_info.name):
                invalid_reason = f"Invalid column name: {column_info.name}."
                invalid_reason_list.append(invalid_reason)
            if column_info.type not in ["INT", "TEXT"]:
                invalid_reason = f"Invalid column type of column {column_info.name}: {column_info.type}."
                invalid_reason_list.append(invalid_reason)
        # endregion
        # region Validate the SQL execution
        assert cls._pseudo_db_bench is not None  # Type narrowing
        try:
            _ = cls._pseudo_db_bench.execute_sql(sql, table_name, column_info_list, [])
        except Exception as e:
            invalid_reason = f"SQL execution failed. Detail: {str(e)}."
            invalid_reason_list.append(invalid_reason)
        # endregion
        # region If the SQL contains serious errors, we do not need to parse it to AST. It cannot be used anyway.
        if len(invalid_reason_list) != 0:
            return SQLValidationResult(
                generation_info=SQLGenerationInfo(
                    sql=sql,
                    column_info_list=column_info_list,
                    table_name=table_name,
                    invalid_reason=construct_complete_invalid_reason(
                        invalid_reason_list
                    ),
                ),
                validation_status=SQLEntryValidationStatus.CANNOT_BE_REUSED,
            )
        del invalid_reason_list
        # endregion
        # region Now, we check whether the SQL contains enough skills
        ast = sqlglot.parse_one(sql)
        sql_skill_list = sorted(SkillEvaluator.evaluate(ast))
        overlapped_skill_count = len(set(sql_skill_list) & set(target_skill_list))
        if overlapped_skill_count < SQLFactory._get_skill_count_threshold(
            len(target_skill_list)
        ):
            invalid_reason = (
                f"The SQL does not relate to enough skills. "
                f"target_skill_list: {sorted(target_skill_list)}."
            )
            return SQLValidationResult(
                generation_info=SQLGenerationInfo(
                    sql=sql,
                    column_info_list=column_info_list,
                    table_name=table_name,
                    skill_list=sql_skill_list,
                    invalid_reason=invalid_reason,
                ),
                validation_status=SQLEntryValidationStatus.CAN_BE_REUSED,
            )
        else:
            return SQLValidationResult(
                generation_info=SQLGenerationInfo(
                    sql=sql,
                    column_info_list=column_info_list,
                    table_name=table_name,
                    skill_list=sql_skill_list,
                ),
                validation_status=SQLEntryValidationStatus.VALID,
            )
        # endregion

    @staticmethod
    def _reuse_sql_entry(
        target_skill_list: Sequence[str],
        invalid_sql_entry_list_json_access_utility: ExclusiveJsonAccessUtility,
        valid_sql_entry_list_json_access_utility: ExclusiveJsonAccessUtility,
    ) -> list[SQLEntry]:
        # region Move reused SQL entries to new_buffered_sql_entry_list
        original_buffered_sql_entry_list: list[SQLEntry] = [
            SQLEntry.model_validate(sql_entry_dict)
            for sql_entry_dict in invalid_sql_entry_list_json_access_utility.read()
        ]
        reused_sql_entry_list: list[SQLEntry] = []
        new_buffered_sql_entry_list: list[SQLEntry] = []
        for sql_entry in original_buffered_sql_entry_list:
            skill_list = sql_entry.generation_info_list[-1].skill_list
            if skill_list is None:
                continue
            overlapped_skill_count = len(set(skill_list) & set(target_skill_list))
            # It is better to check SQLEntry.validation_status here. However, it is not necessary to do that.
            # SQLEntry that cannot be reused will have empty skill_list.
            if overlapped_skill_count >= SQLFactory._get_skill_count_threshold(
                len(target_skill_list)
            ):
                sql_entry.validation_status = SQLEntryValidationStatus.REUSED
                sql_entry.target_skill_list = target_skill_list
                reused_sql_entry_list.append(sql_entry)
            else:
                new_buffered_sql_entry_list.append(sql_entry)
        # endregion
        # region Write new_buffered_sql_entry_list to invalid_sql_entry_list
        invalid_sql_entry_list_json_access_utility.write(
            [sql_entry.model_dump() for sql_entry in new_buffered_sql_entry_list],
        )
        original_valid_sql_entry_list = [
            SQLEntry.model_validate(sql_entry_dict)
            for sql_entry_dict in valid_sql_entry_list_json_access_utility.read()
        ]
        valid_sql_entry_list_json_access_utility.write(
            [
                sql_entry.model_dump()
                for sql_entry in original_valid_sql_entry_list + reused_sql_entry_list
            ],
        )
        # endregion
        return reused_sql_entry_list

    @staticmethod
    def _maintain_table_name_info_dict(
        valid_sql_entry_list_json_access_utility: ExclusiveJsonAccessUtility,
        table_name_info_dict_json_access_utility: ExclusiveJsonAccessUtility,
    ) -> None:
        valid_sql_entry_list: list[SQLEntry] = [
            SQLEntry.model_validate(sql_entry_dict)
            for sql_entry_dict in valid_sql_entry_list_json_access_utility.read()
        ]
        table_name_info_dict: dict[str, dict[str, int]] = {}
        for sql_entry in valid_sql_entry_list:
            scenario = sql_entry.scenario
            if scenario not in table_name_info_dict:
                table_name_info_dict[scenario] = {}
            table_name = sql_entry.generation_info_list[-1].table_name
            if table_name not in table_name_info_dict[scenario]:
                table_name_info_dict[scenario][table_name] = 0
            table_name_info_dict[scenario][table_name] += 1
        table_name_info_dict_json_access_utility.write(table_name_info_dict)

    def _generate_from_target_skill_list(
        self,
        target_skill_list: Sequence[str],
        scenario: str,
        frequent_table_name_list: Optional[Sequence[str]],
        model_name: str,
    ) -> SQLEntry:
        # region Construct message_list
        content: str = SQLFactory._construct_prompt(
            target_skill_list, scenario, frequent_table_name_list
        )
        message_list: list[ChatCompletionMessageParam] = [
            {
                "role": "user",
                "content": content,
            }
        ]
        del content
        # endregion
        token_usage_info_list: list[TokenUsageInfo] = []
        invalid_reason_list: list[str] = []
        generation_info_list: list[SQLGenerationInfo] = []
        for sql_generation_round_index in range(
            self.generation_attempt_count_per_target_skill_list
        ):
            # region Send request to model
            try:
                chat_completion, token_usage_info = (
                    DataFactoryUtility.get_single_chat_completion(
                        self.client,
                        model_name,
                        message_list,
                        self.token_usage_info_list_path,
                        log_prefix="SQL Generation: ",
                    )
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to extract useful chat_completion. {sql_generation_round_index=}"
                )
                raise OpenaiCompletionException(str(e)) from e
            token_usage_info_list.append(token_usage_info)
            assert (
                chat_completion.choices[0].message.content is not None
            )  # Type narrowing
            content = chat_completion.choices[0].message.content
            message_list.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )
            # endregion
            # region Extract sql and other information
            try:
                sql_entry_dict = (
                    DataFactoryUtility.extract_json_object_from_chat_completion_content(
                        content, ["table_name", "column_info_list", "sql"]
                    )
                )
            except JSONObjectExtractionException as e:
                invalid_reason = str(e)
                self.logger.error(invalid_reason)
                invalid_reason_list.append(
                    f"Reason from the SQL generation process: {invalid_reason}"
                )
                message_list.append(
                    {"role": "user", "content": f"{invalid_reason} Please try again."}
                )
                continue
            # endregion
            # region Validate the sql entry
            column_info_list = [
                ColumnInfo.model_validate(column_info)
                for column_info in sql_entry_dict["column_info_list"]
            ]
            sql_validation_result = SQLFactory._validate_sql(
                target_skill_list,
                sql_entry_dict["sql"],
                sql_entry_dict["table_name"],
                column_info_list,
            )
            if sql_validation_result.generation_info.invalid_reason is not None:
                invalid_reason = sql_validation_result.generation_info.invalid_reason
                self.logger.error(invalid_reason)
                invalid_reason_list.append(
                    f"Reason from the SQL validation process: {invalid_reason}"
                )
                message_list.append(
                    {"role": "user", "content": f"{invalid_reason} Please try again."}
                )
            generation_info = sql_validation_result.generation_info
            generation_info_list.append(generation_info)
            if sql_validation_result.validation_status in (
                SQLEntryValidationStatus.VALID,
                SQLEntryValidationStatus.CAN_BE_REUSED,
            ):
                return SQLEntry(
                    generation_info_list=generation_info_list,
                    validation_status=sql_validation_result.validation_status,
                    target_skill_list=target_skill_list,
                    scenario=scenario,
                    token_usage_info_list=token_usage_info_list,
                )
            else:
                # message_list is already be updated with the invalid_reason from the validation process.
                continue
            # endregion
        return SQLEntry(
            generation_info_list=generation_info_list,
            validation_status=SQLEntryValidationStatus.CANNOT_BE_REUSED,
            target_skill_list=target_skill_list,
            scenario=scenario,
            token_usage_info_list=token_usage_info_list,
        )

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
            # region Get target_skill_list
            target_skill_list = self._generate_target_skill_list()
            self.logger.info(f"Get target_skill_list: {target_skill_list}")
            if len(target_skill_list) == 0:
                self.logger.info(f"Generation is finished.")
                break
            # endregion
            # region Reuse SQL entries
            with ExclusiveJsonAccessUtility(
                self.valid_sql_entry_list_path
            ) as valid_sql_entry_list_json_access_utility:
                with ExclusiveJsonAccessUtility(
                    self.invalid_sql_entry_list_path
                ) as invalid_sql_entry_list_json_access_utility:
                    with ExclusiveJsonAccessUtility(
                        self.table_name_info_dict_path
                    ) as table_name_info_dict_json_access_utility:
                        reused_sql_entry_list = SQLFactory._reuse_sql_entry(
                            target_skill_list,
                            invalid_sql_entry_list_json_access_utility,
                            valid_sql_entry_list_json_access_utility,
                        )
                        if len(reused_sql_entry_list) != 0:
                            consecutive_failure_count = 0
                            SQLFactory._maintain_table_name_info_dict(
                                valid_sql_entry_list_json_access_utility,
                                table_name_info_dict_json_access_utility,
                            )
                            self.logger.info(
                                f"Reuse {len(reused_sql_entry_list)} SQL entries. Set consecutive_failure_count to 0."
                            )
                            continue
            # endregion
            # region Get scenario and frequent_table_name_list
            scenario = random.choice(self.scenario_list)
            with ExclusiveJsonAccessUtility(
                self.table_name_info_dict_path
            ) as json_access_utility:
                table_name_info_dict: dict[str, dict[str, int]] = (
                    json_access_utility.read()
                )
                frequent_table_name_list: Optional[list[str]]
                if scenario not in table_name_info_dict:
                    frequent_table_name_list = None
                else:
                    frequent_table_name_list = [
                        table_name
                        for table_name, _ in sorted(
                            table_name_info_dict[scenario].items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                    ][:3]
            # endregion
            # region Get valid_sql_entry_list and invalid_sql_entry_list
            valid_sql_entry: Optional[SQLEntry] = None
            invalid_sql_entry_list: list[SQLEntry] = []
            for model_name in self.model_name_list:
                self.logger.info(f"Start to generate SQL using model {model_name}.")
                try:
                    sql_entry = self._generate_from_target_skill_list(
                        target_skill_list,
                        scenario,
                        frequent_table_name_list,
                        model_name,
                    )
                except OpenaiCompletionException as e:
                    self.logger.error(str(e))
                    continue
                if sql_entry.validation_status != SQLEntryValidationStatus.VALID:
                    invalid_sql_entry_list.append(sql_entry)
                else:
                    valid_sql_entry = sql_entry
                    break
            # endregion
            # region Maintain consecutive_failure_count, write results
            if valid_sql_entry is None:
                consecutive_failure_count += 1
                self.logger.error(
                    f"Failed to generate SQL. "
                    f"Consecutive failure count: {consecutive_failure_count}"
                )
            else:
                consecutive_failure_count = 0
                # region Deduplicate, write results
                with ExclusiveJsonAccessUtility(
                    self.valid_sql_entry_list_path
                ) as valid_sql_entry_list_json_access_utility:
                    with ExclusiveJsonAccessUtility(
                        self.table_name_info_dict_path
                    ) as table_name_info_dict_json_access_utility:
                        # region Deduplicate valid_sql_entry_list, write results
                        original_valid_sql_entry_list: list[SQLEntry] = [
                            SQLEntry.model_validate(sql_entry_dict)
                            for sql_entry_dict in valid_sql_entry_list_json_access_utility.read()
                        ]
                        deduplicated_valid_sql_entry_list: list[SQLEntry] = []
                        existed_valid_sql_set: set[str] = set()
                        for sql_entry in original_valid_sql_entry_list + [
                            valid_sql_entry
                        ]:
                            sql = sql_entry.generation_info_list[-1].sql
                            if sql not in existed_valid_sql_set:
                                deduplicated_valid_sql_entry_list.append(sql_entry)
                                existed_valid_sql_set.add(sql)
                        valid_sql_entry_list_json_access_utility.write(
                            [
                                sql_entry.model_dump()
                                for sql_entry in deduplicated_valid_sql_entry_list
                            ],
                        )
                        self.logger.info(
                            f"Current valid_sql_entry_list length: {len(deduplicated_valid_sql_entry_list)}"
                        )
                        # endregion
                        # region Write table_name_info_dict
                        SQLFactory._maintain_table_name_info_dict(
                            valid_sql_entry_list_json_access_utility,
                            table_name_info_dict_json_access_utility,
                        )
                        # endregion
                # endregion
            # endregion
            # region Write invalid_sql_entry_list
            with ExclusiveJsonAccessUtility(
                self.invalid_sql_entry_list_path
            ) as json_access_utility:
                original_invalid_sql_entry_list: list[SQLEntry] = [
                    SQLEntry.model_validate(sql_entry_dict)
                    for sql_entry_dict in json_access_utility.read()
                ]
                new_invalid_sql_entry_list: Sequence[SQLEntry] = (
                    original_invalid_sql_entry_list + invalid_sql_entry_list
                )
                json_access_utility.write(
                    [
                        sql_entry.model_dump()
                        for sql_entry in new_invalid_sql_entry_list
                    ],
                )
                self.logger.info(
                    f"Current invalid_sql_entry_list length: {len(new_invalid_sql_entry_list)}"
                )
            # endregion


def main() -> None:
    SQLFactory.set_pseudo_db_bench(PseudoDBBench(sql_execution_interval=2))

    def worker() -> None:
        sql_factory = SQLFactory(
            output_dir="./data/v0303/db_bench/raw/sql_factory/v0316",
            minimum_sample_count_per_skill=100,
            minimum_total_sample_count=1000,
            log_file_path="./outputs/data/v0303/db_bench/sql_factory.log",
            generation_attempt_count_per_target_skill_list=5,
            maximum_consecutive_failure_count=20,
            model_name_list=["deepseek-reasoner"],
            enforce_deepseek_discount_flag=False,
        )
        sql_factory.construct()

    thread_count = 32
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(worker) for _ in range(thread_count)]
        for future in concurrent.futures.as_completed(futures):
            # This will re‑raise any exceptions that occurred in the worker
            future.result()


if __name__ == "__main__":
    main()
