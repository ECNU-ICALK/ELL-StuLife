from openai.types.chat import ChatCompletionMessageParam
import json
import re
from typing import Optional, Sequence, Any, Mapping, Self
from pydantic import BaseModel
import concurrent.futures
import threading
import hashlib

from src.factories.data.standard_v0303.utility import (
    TokenUsageInfo,
    OpenaiCompletionException,
    DataFactoryUtility,
    JSONObjectExtractionException,
)
from src.factories.data.standard_v0303.instance.db_bench.sql_factory import (
    SQLExecutionResult,
    PseudoDBBench,
)
from src.factories.data.standard_v0303.instance.db_bench.instruction_factory import (
    SQLInstructionEntry,
    InstructionFactory,
)
from src.factories.data.standard_v0303.instance.db_bench.demonstration import (
    ROW_FACTORY_DEMONSTRATION_INFO_DICT,
)
from src.factories.data.standard_v0303.instance.db_bench.utility import (
    GenerationArgument,
    GenerationResult,
    DBBenchDataFactory,
)
from src.tasks.instance.db_bench.task import (
    DBBenchType,
    ColumnInfo,
)


class RowListValidationResult(BaseModel):
    invalid_reason: Optional[str] = None
    processed_row_list: Optional[Sequence[DBBenchType.Row]] = None
    row_modification_info_list: Optional[Sequence[str]] = None
    sql_execution_result: Optional[SQLExecutionResult] = None


class SQLInstructionRowListEntry(BaseModel):
    sql_instruction_entry: SQLInstructionEntry
    token_usage_info_list: Sequence[TokenUsageInfo]
    invalid_reason_list: Optional[Sequence[str]]
    validation_result_list: Sequence[RowListValidationResult]

    def __hash__(self) -> int:
        serialized = str(self.model_dump()).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return int(digest, 16)


class RowListFactory(
    DBBenchDataFactory[SQLInstructionEntry, SQLInstructionRowListEntry]
):
    _pseudo_db_bench_lock: threading.Lock = threading.Lock()
    _pseudo_db_bench: Optional[PseudoDBBench] = None

    def __init__(
        self,
        instruction_factory_output_dir: str,
        output_dir: str,
        log_file_path: str,
        model_name_list: Sequence[str],
        maximum_consecutive_failure_count: int,
        enforce_deepseek_discount_flag: bool,
        generation_attempt_count_per_sql_instruction_entry: int,
    ):
        assert RowListFactory._pseudo_db_bench is not None
        valid_low_level_entry_output_path = (
            InstructionFactory.get_valid_current_level_entry_list_path(
                instruction_factory_output_dir
            )
        )
        self.generation_attempt_count_per_sql_instruction_entry = (
            generation_attempt_count_per_sql_instruction_entry
        )
        super().__init__(
            valid_low_level_entry_output_path,
            output_dir,
            log_file_path,
            model_name_list,
            maximum_consecutive_failure_count,
            enforce_deepseek_discount_flag,
            SQLInstructionEntry,
            SQLInstructionRowListEntry,
        )

    @staticmethod
    def _extract_low_level_entry_from_current_level_entry(
        current_level_entry: SQLInstructionRowListEntry,
    ) -> SQLInstructionEntry:
        return current_level_entry.sql_instruction_entry

    @staticmethod
    def _get_column_info_str(column_info_list: Sequence[ColumnInfo]) -> str:
        column_info_str = ""
        for column_info in column_info_list:
            column_info_str += f"- {column_info.name} ({column_info.type})\n"
        column_info_str = column_info_str[:-1]
        return column_info_str

    @staticmethod
    def _construct_prompt(sql_instruction_entry: SQLInstructionEntry) -> str:
        # region Get sql, table_name
        sql: str = sql_instruction_entry.sql_entry.generation_info_list[-1].sql
        table_name: str = sql_instruction_entry.sql_entry.generation_info_list[
            -1
        ].table_name
        # endregion
        # region Construct specified_requirement_based_on_sql
        specified_requirement_based_on_sql: str
        if sql.upper().startswith("SELECT"):
            specified_requirement_based_on_sql = """
    - The provided SQL query is a SELECT query. For the SELECT query, The table must contain data such that the SELECT query returns at least one row.
    - If the query includes one or more WHERE clauses, the table’s data should ensure that at least one WHERE clause is effective. This means that
        - Some rows must satisfy the condition(s) (and thus be selected or used in aggregation).
        - Other rows must not satisfy the condition(s) (and thus be excluded).
    - Ideally, as many of the specified WHERE conditions as possible should actually impact the result."""
        elif sql.upper().startswith("INSERT"):
            specified_requirement_based_on_sql = "\n    - The provided SQL query is an INSERT query. The table does not define a primary key, so the table can contain duplicate rows."
        elif sql.upper().startswith("UPDATE"):
            specified_requirement_based_on_sql = "\n    - The provided SQL query is an UPDATE query. For the UPDATE query, the table must contain data such that the UPDATE statement to update at least one row in the table."
        else:
            # sql.upper().startswith('DELETE')
            specified_requirement_based_on_sql = "\n    - The provided SQL query is a DELETE query. For the DELETE query, the table must contain data such that the DELETE statement to delete at least one row in the table."
        # endregion
        # region Construct specified_demonstration_based_on_sql
        demonstration_dict: Mapping[str, Any]
        if sql.upper().startswith("SELECT"):
            demonstration_dict = ROW_FACTORY_DEMONSTRATION_INFO_DICT["SELECT"]
        elif sql.upper().startswith("INSERT"):
            demonstration_dict = ROW_FACTORY_DEMONSTRATION_INFO_DICT["INSERT"]
        elif sql.upper().startswith("UPDATE"):
            demonstration_dict = ROW_FACTORY_DEMONSTRATION_INFO_DICT["UPDATE"]
        else:
            # sql.upper().startswith('DELETE')
            demonstration_dict = ROW_FACTORY_DEMONSTRATION_INFO_DICT["DELETE"]
        demonstration_row_str: str = json.dumps(
            f"{{row_list: {demonstration_dict['rows']}}}", indent=4
        )
        specified_demonstration_based_on_sql: str = (
            f"""
    - Instruction: {demonstration_dict['instruction']}
    - Ground truth SQL: {demonstration_dict['sql']}
    - Table name: {demonstration_dict['table_name']}
    - Generated rows in the output format: {demonstration_row_str}
    - Explanation: {demonstration_dict['explanation']}"""[
                1:
            ]
        )  # Remove the first newline character
        # endregion
        # region Construct column_info_str
        column_info_list = sql_instruction_entry.sql_entry.generation_info_list[
            -1
        ].column_info_list
        column_info_str = RowListFactory._get_column_info_str(column_info_list)
        # endregion
        # region Construct prompt
        prompt = f"""I am building a database benchmarking task using SQL queries. During the test, the user will be provided with an instruction, and their job is to write a SQL query corresponding to the instruction. The SQL query will be actually executed in the database, and the correctness of the user-written SQL query will be judged based on the evaluation results of the ground truth SQL query and the user-written SQL query. Current, the instruction, the ground truth SQL query, and the definition of the table have already be constructed, but the content of the table is left unfilled.

Now you will be provided with the instruction, the ground truth SQL query, and the definition of the table. You task is to fill the table with value,  so that the execution result of the SQL entries can be used to judge to correctness of the user-written SQL query.

1. Output Format:
    - The response must contain a JSON object encapsulated within a ```json``` code block.
    - The JSON object must include the following key:
        - row_list (list[list[int | str |, ...]]): Represent the table as a list of lists, where each inner list corresponds to a single row. Each inner list must meet the following criteria.
            - Matching Length: The number of elements in each inner list must exactly equal the number of columns in the table.
            - Type Consistency: Every element in an inner list must have the same data type as the corresponding column in the table.
            - Column Order Alignment: The order of elements in each inner list must exactly match the order of the table's columns.

2. Basic Requirements:
    - The table must contain at least 20 rows, and at most 50 rows.
    - The definitions of the columns in the table are already determined. If the column has the type "INT", the value in the column must be an integer. If the column has the type "TEXT", the value in the column must be a string.
    - Do not include the following characters in the table: double quotation marks (""), single quotation marks ('), brackets (()), comma (,), backquote(`), and backslash (\).
    - Do not include any NULL values in the table.
    - There should not be identical rows in the table.
    - After the generation, rows that are duplicate will be removed. If a value contains an invalid character, the invalid character will be replaced with an underscore. So, Do not generate duplicate rows or invalid rows.
    - If a column in the type of "TEXT" is used to describe the date, you should use the format "YYYY-MM-DD" (e.g., "2022-01-01") to represent the date in each row.{specified_requirement_based_on_sql}

3. Below are the demonstration. The demonstration is simple and may not be good enough, but it can help you understand the requirements.
{specified_demonstration_based_on_sql}

4. Now, Please generate the rows based on the provided SQL query and other information.
SQL query: {sql}
Table name: {table_name}
The definition of the columns is listed below. Please note that some columns may not be used in the SQL query.
{column_info_str}
Instruction: {sql_instruction_entry.instruction_list[-1]}
"""
        # endregion
        return prompt

    @classmethod
    def set_pseudo_db_bench(cls, pseudo_db_bench: PseudoDBBench) -> None:
        cls._pseudo_db_bench = pseudo_db_bench

    def _validate_row_list(
        self,
        original_row_list: Sequence[DBBenchType.Row],
        sql_instruction_entry: SQLInstructionEntry,
    ) -> RowListValidationResult:
        # region Get column_info_list
        column_info_list = sql_instruction_entry.sql_entry.generation_info_list[
            -1
        ].column_info_list
        # endregion
        # region Ensure that there is at least one row
        if len(original_row_list) == 0:
            return RowListValidationResult(invalid_reason="The row_list is empty.")
        # endregion
        # region Check column count
        column_count_set: set[int] = set()
        for row in original_row_list:
            column_count_set.add(len(row))
        if len(column_count_set) > 1:
            return RowListValidationResult(
                invalid_reason="The number of columns in the rows is not consistent."
            )
        actual_column_count = column_count_set.pop()
        expected_column_count = len(column_info_list)
        if actual_column_count != expected_column_count:
            column_info_str = RowListFactory._get_column_info_str(column_info_list)
            return RowListValidationResult(
                invalid_reason=(
                    f"The number of columns in the rows does not match the number of columns in the table. "
                    f"There should be {expected_column_count} columns. "
                    f"You generated {actual_column_count} columns for each row.\n"
                    f"Column information:\n{column_info_str}"
                )
            )
        # endregion
        # region Check column type consistency
        # region Ensure that all the type in the column is the same and known (i.e., INT or TEXT)
        type_set_list: list[set[str]] = [set() for _ in range(actual_column_count)]
        for row in original_row_list:
            for value_index, value in enumerate(row):
                if isinstance(value, int):
                    type_set_list[value_index].add("INT")
                elif isinstance(value, str):
                    type_set_list[value_index].add("TEXT")
                else:
                    type_set_list[value_index].add("UNKNOWN")
        invalid_reason: Optional[str] = None
        # region Check for consistency
        inconsistent_column_index_list: list[int] = []
        for column_index, type_set in enumerate(type_set_list):
            if len(type_set) > 1:
                inconsistent_column_index_list.append(column_index)
        if len(inconsistent_column_index_list) != 0:
            inconsistent_column_name_str = ", ".join(
                column_info_list[column_index].name
                for column_index in inconsistent_column_index_list
            )
            invalid_reason = (
                f"The following columns have inconsistent data types: "
                f"{inconsistent_column_name_str}.\n"
            )
        # endregion
        # region Check for unknown type
        unknown_column_index_list: list[int] = []
        for column_index, type_set in enumerate(type_set_list):
            if "UNKNOWN" in type_set:
                unknown_column_index_list.append(column_index)
        if len(unknown_column_index_list) != 0:
            unknown_column_name_str = ", ".join(
                column_info_list[column_index].name
                for column_index in unknown_column_index_list
            )
            local_invalid_reason = (
                f"The following columns contain data that are not in the form of INT or TEXT: "
                f"{unknown_column_name_str}.\n"
            )
            if invalid_reason is None:
                invalid_reason = local_invalid_reason
            else:
                invalid_reason += local_invalid_reason
        # endregion
        if invalid_reason is not None:
            column_info_str = RowListFactory._get_column_info_str(column_info_list)
            invalid_reason += f"Column information:\n{column_info_str}"
            return RowListValidationResult(invalid_reason=invalid_reason)
        del invalid_reason
        # endregion
        # region Check the correctness of the data type
        incorrect_column_type_list: list[Optional[str]] = []
        for column_index, type_set in enumerate(type_set_list):
            actual_column_type = type_set.pop()
            expected_column_type = column_info_list[column_index].type
            if actual_column_type != expected_column_type:
                incorrect_column_type_list.append(actual_column_type)
            else:
                incorrect_column_type_list.append(None)  # placeholder
        if any(incorrect_column_type_list):
            incorrect_column_info_str = ""
            for column_index, incorrect_actual_column_type in enumerate(
                incorrect_column_type_list
            ):
                if incorrect_actual_column_type is None:
                    continue
                column_name = column_info_list[column_index].name
                expected_column_type = column_info_list[column_index].type
                incorrect_column_info_str += (
                    f"\t- Column name: {column_name}, "
                    f"Actual type: {incorrect_actual_column_type}, "
                    f"Expected type: {expected_column_type}\n"
                )
            incorrect_column_info_str = incorrect_column_info_str[
                :-1
            ]  # Remove the last newline character
            column_info_str = RowListFactory._get_column_info_str(column_info_list)
            return RowListValidationResult(
                invalid_reason=(
                    f"The data types in the columns are incorrect. "
                    f"The following columns have incorrect data types:\n"
                    f"{incorrect_column_info_str}\n"
                    f"Column information:\n{column_info_str}"
                )
            )
        # endregion  # noqa
        # endregion
        # region Check the value of the rows
        # Used to record the modification and removal of rows
        # Only record original row_index in the row_modification_info_list
        row_modification_info_list: Optional[list[str]] = None
        processed_row_list: list[DBBenchType.Row] = []
        # existed_row_set is only used to check for duplication
        existed_row_set: set[DBBenchType.Row] = set()
        for row_index, row in enumerate(original_row_list):
            # region Check for duplication
            if row in existed_row_set:
                another_row_index = processed_row_list.index(row)
                if row_modification_info_list is None:
                    row_modification_info_list = []
                row_modification_info_list.append(
                    f"Row with the index {row_index} is identical to the row with the index {another_row_index}. "
                    f"It is not included in the processed_row_list."
                )
                continue
            else:
                existed_row_set.add(row)
            # endregion
            processed_row: list[DBBenchType.RowValue] = []
            # region Check for invalid characters
            modification_flag: bool = False
            for column_index, column_info in enumerate(column_info_list):
                if column_info.type == "TEXT":
                    # str() is not necessary, it is used for type narrowing
                    raw_str = str(row[column_index])
                    processed_str = re.sub(r"[\"\'(),`\\]", "_", raw_str)
                    modification_flag = modification_flag or raw_str != processed_str
                    processed_row.append(processed_str)
                elif column_info.type == "INT":
                    processed_row.append(row[column_index])
                else:
                    raise NotImplementedError("The column type is not supported.")
            if modification_flag:
                if row_modification_info_list is None:
                    row_modification_info_list = []
                row_modification_info_list.append(
                    f"Row with the index {row_index} contains invalid characters. "
                    f"The invalid characters have been replaced with underscores."
                )
            # endregion
            processed_row_list.append(tuple(processed_row))
        del existed_row_set
        # endregion
        # region Execute the SQL
        try:
            assert RowListFactory._pseudo_db_bench is not None  # Type narrowing
            sql_execution_result = RowListFactory._pseudo_db_bench.execute_sql(
                sql_instruction_entry.sql_entry.generation_info_list[-1].sql,
                sql_instruction_entry.sql_entry.generation_info_list[-1].table_name,
                sql_instruction_entry.sql_entry.generation_info_list[
                    -1
                ].column_info_list,
                processed_row_list,
            )
        except Exception as e:
            invalid_reason = f"Error happened in executing the SQL: {str(e)}"
            return RowListValidationResult(
                invalid_reason=invalid_reason,
                row_modification_info_list=row_modification_info_list,
            )
        # endregion
        # region Validate the execution result of SQL
        sql = sql_instruction_entry.sql_entry.generation_info_list[-1].sql
        if sql.startswith("SELECT"):
            assert sql_execution_result.answer_direct is not None
            if len(sql_execution_result.answer_direct) == 0:
                return RowListValidationResult(
                    invalid_reason="The SELECT query does not return any row.",
                    row_modification_info_list=row_modification_info_list,
                    processed_row_list=processed_row_list,
                    sql_execution_result=sql_execution_result,
                )
        else:
            assert (
                sql_execution_result.original_table_md5 is not None
                and sql_execution_result.executed_sql_table_md5 is not None
            )
            if (
                sql_execution_result.original_table_md5
                == sql_execution_result.executed_sql_table_md5
            ):
                return RowListValidationResult(
                    invalid_reason="The SQL query does not change the table.",
                    row_modification_info_list=row_modification_info_list,
                    processed_row_list=processed_row_list,
                    sql_execution_result=sql_execution_result,
                )
        # endregion
        # region All requirements are satisfied
        return RowListValidationResult(
            processed_row_list=processed_row_list,
            row_modification_info_list=row_modification_info_list,
            sql_execution_result=sql_execution_result,
        )  # If the result is valid, the invalid_reason is None
        # endregion

    def _generate_from_low_level_entry(
        self,
        generation_argument: GenerationArgument[SQLInstructionEntry],
    ) -> GenerationResult[SQLInstructionRowListEntry]:
        # region Construct message_list
        prompt = RowListFactory._construct_prompt(generation_argument.low_level_entry)
        message_list: list[ChatCompletionMessageParam] = [
            {
                "role": "user",
                "content": prompt,
            }
        ]
        del prompt
        # endregion
        # region Generate
        token_usage_info_list: list[TokenUsageInfo] = []
        invalid_reason_list: Optional[list[str]] = None
        validation_result_list: list[RowListValidationResult] = []
        for round_index in range(
            self.generation_attempt_count_per_sql_instruction_entry
        ):
            # region Send request to model
            try:
                chat_completion, token_usage_info = (
                    DataFactoryUtility.get_single_chat_completion(
                        self.client,
                        generation_argument.model_name,
                        message_list,
                        self.token_usage_info_list_path,
                    )
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to extract useful chat_completion. {round_index=}"
                )
                raise OpenaiCompletionException(str(e)) from e
            token_usage_info_list.append(token_usage_info)
            content = chat_completion.choices[0].message.content
            assert content is not None  # Type narrowing
            message_list.append({"role": "assistant", "content": content})
            # endregion
            # region Extract row_list
            try:
                row_list_dict = (
                    DataFactoryUtility.extract_json_object_from_chat_completion_content(
                        content, required_key_list=["row_list"]
                    )
                )
            except JSONObjectExtractionException as e:
                invalid_reason = str(e)
                self.logger.error(invalid_reason)
                if invalid_reason_list is None:
                    invalid_reason_list = []
                invalid_reason_list.append(
                    f"Failed to retrieve valid row_list_dict from model chat_completion: {invalid_reason}"
                )
                message_list.append(
                    {"role": "user", "content": f"{invalid_reason} Please try again."}
                )
                continue
            del content
            row_list: Sequence[DBBenchType.Row] = [
                tuple(row) for row in row_list_dict["row_list"]
            ]
            # endregion
            # region Validate row_list
            row_list_validation_result = self._validate_row_list(
                row_list, generation_argument.low_level_entry
            )
            validation_result_list.append(row_list_validation_result)
            # endregion
            if row_list_validation_result.invalid_reason is None:
                return GenerationResult(
                    current_level_entry=SQLInstructionRowListEntry(
                        sql_instruction_entry=generation_argument.low_level_entry,
                        token_usage_info_list=token_usage_info_list,
                        validation_result_list=validation_result_list,
                        invalid_reason_list=invalid_reason_list,
                    ),
                    success_flag=True,
                )
            else:
                invalid_reason = row_list_validation_result.invalid_reason
                row_modification_info_list = (
                    row_list_validation_result.row_modification_info_list
                )
                self.logger.error(invalid_reason)
                if invalid_reason_list is None:
                    invalid_reason_list = []
                invalid_reason_list.append(
                    f"Failed to validate the row_list: {invalid_reason}\n"
                    f"row_modification_info_list: {row_modification_info_list}"
                )
                user_content = invalid_reason
                if row_modification_info_list is not None:
                    user_content += f"\nPlease be aware that the value of rows that are inserted into the table are modified. The modification information is as follows:\n"
                    for row_modification_info in row_modification_info_list:
                        user_content += f"- {row_modification_info}\n"
                message_list.append({"role": "user", "content": user_content})
                continue
        # endregion
        return GenerationResult(
            current_level_entry=SQLInstructionRowListEntry(
                sql_instruction_entry=generation_argument.low_level_entry,
                token_usage_info_list=token_usage_info_list,
                validation_result_list=validation_result_list,
                invalid_reason_list=invalid_reason_list,
            ),
            success_flag=False,
        )


def main() -> None:
    RowListFactory.set_pseudo_db_bench(PseudoDBBench(sql_execution_interval=5))

    def worker() -> None:
        row_list_factory = RowListFactory(
            instruction_factory_output_dir="data/v0303/db_bench/raw/instruction_factory/v0316",
            output_dir="data/v0303/db_bench/raw/row_list_factory/v0316",
            log_file_path="./outputs/data/v0303/db_bench/row_list_factory.log",
            model_name_list=["deepseek-reasoner"],
            maximum_consecutive_failure_count=20,
            enforce_deepseek_discount_flag=True,
            generation_attempt_count_per_sql_instruction_entry=3,
        )
        row_list_factory.construct()

    thread_count = 32  # noqa
    RowListFactory.unprocessed_low_level_entry_list_initialization_barrier = (
        threading.Barrier(thread_count)
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(worker) for _ in range(thread_count)]
        for future in concurrent.futures.as_completed(futures):
            # This will re‑raise any exceptions that occurred in the worker
            future.result()


if __name__ == "__main__":
    main()
