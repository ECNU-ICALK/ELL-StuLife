from openai.types.chat import ChatCompletionMessageParam
import json
import re
import hashlib
from typing import Optional, Sequence, Any
from pydantic import BaseModel
import concurrent.futures
import threading

from src.factories.data.standard_v0303.utility import (
    TokenUsageInfo,
    ExclusiveJsonAccessUtility,
    OpenaiCompletionException,
    DataFactoryUtility,
    JSONObjectExtractionException,
)
from src.factories.data.standard_v0303.instance.db_bench.sql_factory import (
    SQLEntry,
    SQLFactory,
)
from src.factories.data.standard_v0303.instance.db_bench.demonstration import (
    INSTRUCTION_FACTORY_DEMONSTRATION_INFO_LIST,
)
from src.factories.data.standard_v0303.instance.db_bench.utility import (
    DBBenchGenerationException,
    GenerationArgument,
    GenerationResult,
    DBBenchDataFactory,
)


class InstructionJudgement(BaseModel):
    token_usage_info: TokenUsageInfo
    is_possible: bool
    reason: str


class SQLInstructionEntry(BaseModel):
    sql_entry: SQLEntry
    token_usage_info_list: list[TokenUsageInfo]
    instruction_list: list[str]
    invalid_reason_list: Optional[list[str]]
    judgement_list: list[InstructionJudgement]

    def __hash__(self) -> int:
        serialized = str(self.model_dump()).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return int(digest, 16)


class JudgementExtractionException(DBBenchGenerationException):
    pass


class InstructionFactory(DBBenchDataFactory[SQLEntry, SQLInstructionEntry]):
    def __init__(
        self,
        sql_factory_output_dir: str,
        output_dir: str,
        log_file_path: str,
        model_name_list: Sequence[str],
        maximum_consecutive_failure_count: int,
        enforce_deepseek_discount_flag: bool,
        generation_attempt_count_per_sql_entry: int,
        judgement_attempt_count_per_instruction: int,
    ):
        valid_low_level_entry_output_path = SQLFactory.get_valid_sql_entry_list_path(
            sql_factory_output_dir
        )
        self.generation_attempt_count_per_sql_entry = (
            generation_attempt_count_per_sql_entry
        )
        self.judgement_attempt_count_per_instruction = (
            judgement_attempt_count_per_instruction
        )
        super().__init__(
            valid_low_level_entry_output_path,
            output_dir,
            log_file_path,
            model_name_list,
            maximum_consecutive_failure_count,
            enforce_deepseek_discount_flag,
            SQLEntry,
            SQLInstructionEntry,
        )

    @staticmethod
    def _extract_low_level_entry_from_current_level_entry(
        current_level_entry: SQLInstructionEntry,
    ) -> SQLEntry:
        return current_level_entry.sql_entry

    def _judge_instruction(self, prompt: str, model_name: str) -> InstructionJudgement:
        chat_completion, token_usage_info = (
            DataFactoryUtility.get_single_chat_completion(
                self.client,
                model_name,
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                self.token_usage_info_list_path,
                log_prefix="Judgement: ",
            )
        )
        content = chat_completion.choices[0].message.content
        assert content is not None  # Type narrowing
        try:
            judgement_dict = (
                DataFactoryUtility.extract_json_object_from_chat_completion_content(
                    content,
                    required_key_list=["is_possible", "reason"],
                )
            )
        except JSONObjectExtractionException as e:
            error_message = f"Judgement: {str(e)}"
            self.logger.error(error_message)
            raise JudgementExtractionException(error_message) from e
        is_possible = judgement_dict["is_possible"]
        return InstructionJudgement(
            token_usage_info=token_usage_info,
            is_possible=str(is_possible).lower() == "true",
            reason=judgement_dict["reason"],
        )

    def _generate_from_low_level_entry(
        self,
        generation_argument: GenerationArgument[SQLEntry],
    ) -> GenerationResult[SQLInstructionEntry]:
        # region Get sql
        sql: str = generation_argument.low_level_entry.generation_info_list[-1].sql
        table_name: str = generation_argument.low_level_entry.generation_info_list[
            -1
        ].table_name
        # endregion
        # region Construct demonstration_str
        demonstration_str = ""
        for demonstration_index, demonstration_info in enumerate(
            INSTRUCTION_FACTORY_DEMONSTRATION_INFO_LIST
        ):
            column_info_str = ""
            for _column_info in demonstration_info["column_info_list"]:
                column_info_str += f"""
        - {_column_info['name']} ({_column_info['type']})"""
            column_info_str = column_info_str[1:]
            demonstration_str += f"""Demonstration {demonstration_index + 1}:
    - SQL: {demonstration_info["sql"]}
    - Table name: {demonstration_info["table_name"]}
    - Column info: 
{column_info_str}
    - Instruction: {demonstration_info["instruction"]}
"""
            demonstration_str += "\n"
        # Remove the last two newline characters
        demonstration_str = demonstration_str[:-2]
        # endregion
        # region Construct column_info_str
        column_info_str = ""
        column_info_list = generation_argument.low_level_entry.generation_info_list[
            -1
        ].column_info_list
        for column_info in column_info_list:
            column_info_str += f"- {column_info.name} ({column_info.type})\n"
        column_info_str = column_info_str[:-1]
        # endregion
        # region Construct prompt
        prompt = f"""I am building a database benchmarking task using SQL queries. You will be provided with a SQL query and the information of the table, and I need you to generate an instruction for it. During the test, the user will be provided with the instruction and the definition of the database, and then write the SQL query I provided.

1. Output Format:
    - The response must contain a JSON object encapsulated within a ```json``` code block.
    - The JSON object must include the following key:
        - instruction (str): The instruction for the SQL query.

2. Basic Requirements:
    - You can output other content, but you must include a JSON object with the correct format in the response.
    - Do not include the table name and column names in the instruction, as they will be provided to the user with the instruction.
    - The instruction must clearly describe the SQL query, enabling the user to write the SQL query correctly.
    - For SELECT statements, the instruction must clearly describe the value that the SQL query would return.

3. Below are the demonstrations of the SQL query and the instruction.
{demonstration_str}

4. Now, Please generate an instruction for the SQL query: {sql}
The name of the table is: {table_name}
The definition of the columns is listed below. Please note that some columns may not be used in the SQL query.
{column_info_str}
"""
        # endregion
        # region Construct message_list
        message_list: list[ChatCompletionMessageParam] = [
            {
                "role": "user",
                "content": prompt,
            }
        ]
        del prompt
        # endregion
        token_usage_info_list: list[TokenUsageInfo] = []
        invalid_reason_list: list[str] = []
        instruction_list: list[str] = []
        judgement_list: list[InstructionJudgement] = []
        for instruction_generation_round_index in range(
            self.generation_attempt_count_per_sql_entry
        ):
            # region Generate an instruction
            # region Send request to model
            try:
                chat_completion, token_usage_info = (
                    DataFactoryUtility.get_single_chat_completion(
                        self.client,
                        generation_argument.model_name,
                        message_list,
                        self.token_usage_info_list_path,
                        log_prefix="Instruction Generation: ",
                    )
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to extract useful chat_completion. {instruction_generation_round_index=}"
                )
                raise OpenaiCompletionException(str(e)) from e
            token_usage_info_list.append(token_usage_info)
            content = chat_completion.choices[0].message.content
            assert content is not None  # Type narrowing
            message_list.append({"role": "assistant", "content": content})
            # endregion
            # region Extract instruction from the chat_completion
            try:
                instruction_dict: dict[str, Any] = (
                    DataFactoryUtility.extract_json_object_from_chat_completion_content(
                        content, required_key_list=["instruction"]
                    )
                )
            except JSONObjectExtractionException as e:
                invalid_reason = str(e)
                self.logger.error(invalid_reason)
                invalid_reason_list.append(
                    f"Reason from the generation process: {invalid_reason}"
                )
                message_list.append(
                    {"role": "user", "content": f"{invalid_reason} Please try again."}
                )
                continue
            instruction: str = instruction_dict["instruction"]
            instruction_list.append(instruction)
            self.logger.info(
                f"Extracted an instruction from the model chat_completion: {instruction}."
            )
            # endregion  # noqa
            # endregion
            # region Use another prompt to validate the instruction
            # region Construct judgement prompt
            judgement_prompt = f"""I am building a database benchmarking task using SQL queries. During the test, the user will be provided with the instruction and the definition of the database, and then write the SQL query I provided. The correctness of the user-written SQL query will be judged based on the evaluation results of the ground truth SQL query and the user-written SQL query.

Your task is to judge whether it is possible for the user to write a SQL query that has the same effect as the ground truth SQL query based on the instruction and definition of the database.

1. Output Format:
    - The response must contain a JSON object encapsulated within a ```json``` code block.
    - The JSON object must include the following keys:
        - is_possible (bool): Whether it is possible for user to write a SQL query that has the same effect as the ground truth SQL query based on the instruction and definition of the database. You can only output true or false here.
        - reason (str): The reason for the judgement. You can also provide additional information that can be used to refine the instruction.

3. Basic Requirements:
    - The instruction should be sufficiently clear so that the correct solution precisely fits the SQL.
    - You should focus primarily on whether the logic of the SQL statements matches the description.
    - You can output other content, but you must include a JSON object with the correct format in the response.
    - The instruction is not necessary to include the table name and column names, as they will be provided to the user with the instruction.
    - For SELECT statements, the instruction must clearly describe the value that the SQL query would return.

3. Below are the demonstrations of the SQL query and the instruction. These demonstrations may not be good enough, but they can help you understand the requirements.
{demonstration_str}

4. Now, Please judge whether it is possible for user to write a SQL query that has the same effect as the ground truth SQL query based on the instruction and definition of the database.
SQL query: {sql}
Table name: {table_name}
The definition of the columns is listed below. Please note that some columns may not be used in the SQL query.
{column_info_str}
Instruction: {instruction}
"""
            # endregion
            # region Send request with retry
            judgement: Optional[InstructionJudgement] = None
            for judgement_retry_index in range(
                self.judgement_attempt_count_per_instruction
            ):
                try:
                    judgement = self._judge_instruction(
                        judgement_prompt, generation_argument.model_name
                    )
                except OpenaiCompletionException as e:
                    # Unknown error happened, and it needs to be handled by the caller
                    error_message = "Instruction Generation: Cannot get the judgement of the instruction."
                    self.logger.error(error_message)
                    raise OpenaiCompletionException(error_message) from e
                except JudgementExtractionException:
                    self.logger.error(f"{judgement_retry_index=}. Judgement failed.")
                    continue
                break  # Break the loop if no exception is raised
            if judgement is None:
                error_message = (
                    f"Judgement failed for {self.judgement_attempt_count_per_instruction} times. "
                    f"Instruction: {instruction}"
                )
                self.logger.error(error_message)
                raise JudgementExtractionException(error_message)
            judgement_list.append(judgement)
            if judgement.is_possible:
                return GenerationResult(
                    success_flag=True,
                    current_level_entry=SQLInstructionEntry(
                        sql_entry=generation_argument.low_level_entry,
                        token_usage_info_list=token_usage_info_list,
                        instruction_list=instruction_list,  # Will always have at least one element
                        invalid_reason_list=(
                            invalid_reason_list
                            if len(invalid_reason_list) > 0
                            else None
                        ),
                        judgement_list=judgement_list,
                    ),
                )
            else:
                judgement_index = len(judgement_list) - 1
                invalid_reason_list.append(
                    f"Reason from the judgement process: "
                    f"judgement_index: <JUDGEMENT_INDEX_START>{judgement_index}<JUDGEMENT_INDEX_END>"
                )
                message_list.append(
                    {
                        "role": "user",
                        "content": (
                            f"Previous generation is not good enough. Reason: {judgement.reason}. "
                            f"Please try again."
                        ),
                    }
                )
                continue
            # endregion
            # endregion
        return GenerationResult(
            success_flag=False,
            current_level_entry=SQLInstructionEntry(
                sql_entry=generation_argument.low_level_entry,
                token_usage_info_list=token_usage_info_list,
                instruction_list=instruction_list,  # Will always have at least one element
                invalid_reason_list=(
                    invalid_reason_list if len(invalid_reason_list) > 0 else None
                ),
                judgement_list=judgement_list,
            ),
        )


def main() -> None:
    def worker() -> None:
        instruction_factory = InstructionFactory(
            sql_factory_output_dir="./data/v0303/db_bench/raw/sql_factory/v0316",
            output_dir="./data/v0303/db_bench/raw/instruction_factory/v0316",
            log_file_path="./outputs/data/v0303/db_bench/instruction_factory.log",
            generation_attempt_count_per_sql_entry=3,
            judgement_attempt_count_per_instruction=3,
            model_name_list=["deepseek-reasoner"],
            maximum_consecutive_failure_count=20,
            enforce_deepseek_discount_flag=True,
        )
        instruction_factory.construct()

    thread_count = 20  # noqa
    InstructionFactory.unprocessed_low_level_entry_list_initialization_barrier = (
        threading.Barrier(thread_count)
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(worker) for _ in range(thread_count)]
        for future in concurrent.futures.as_completed(futures):
            # This will re‑raise any exceptions that occurred in the worker
            future.result()


if __name__ == "__main__":
    main()
