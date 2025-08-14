import json
import os
from typing import Sequence, Any, Mapping, Optional
import random
from pydantic import BaseModel
import datetime

from src.factories.data.standard_v0303.instance.db_bench.row_list_factory import (
    SQLInstructionRowListEntry,
    RowListFactory,
)
from src.tasks.instance.db_bench.task import (
    DBBench,
    DirectTypeAnswerValidator,
    DBBenchDatasetItem,
    AnswerType,
)
from src.tasks.instance.db_bench.container import DBBenchContainer
from src.utils import SingletonLogger
from src.typings import LoggerConfig


class DatasetInfo(BaseModel):
    sql_instruction_row_list_entry_path: str
    sql_instruction_row_list_entry_path_length: int
    sample_count: int
    random_seed: int
    output_dir: str
    created_time: str
    index_dict: Mapping[int, int]  # current_index -> original_index


class PseudoDBBench:
    def __init__(self) -> None:
        self.container = DBBenchContainer()
        self.current_dataset_item: Optional[DBBenchDatasetItem] = None

    def _get_current_dataset_item(self) -> DBBenchDatasetItem:
        assert self.current_dataset_item is not None
        return self.current_dataset_item


class EntryFactory:
    def __init__(
        self,
        row_list_factory_output_dir: str,
        output_dir: str,
        log_file_path: str,
        random_seed: int,
    ):
        self.row_list_factory_output_dir = row_list_factory_output_dir
        self.output_dir = output_dir
        self.random_seed = random_seed
        logger_config = LoggerConfig(
            level="INFO",
            log_file_path=log_file_path,
            logger_name="db_bench_standard_data_factory",
        )
        self.logger = SingletonLogger.get_instance(logger_config)

    def _get_output_path_dict(self) -> Mapping[str, str]:
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        entry_dict_output_path = os.path.join(self.output_dir, "entry_dict.json")
        dataset_info_output_path = os.path.join(self.output_dir, "dataset_info.json")
        return {
            "entry_dict_output_path": entry_dict_output_path,
            "dataset_info_output_path": dataset_info_output_path,
        }

    def random_order_construct(self, sample_count: Optional[int] = None) -> None:
        """
        If sample_count is None, all the entries will be processed.
        However, the order of the entries will still be shuffled.
        """
        # region Get sql_instruction_row_list_entry_list, prepare
        random.seed(self.random_seed)
        sql_instruction_row_list_entry_path = (
            RowListFactory.get_valid_current_level_entry_list_path(
                self.row_list_factory_output_dir
            )
        )
        sql_instruction_row_list_entry_list: Sequence[SQLInstructionRowListEntry] = [
            SQLInstructionRowListEntry.model_validate(entry_dict)
            for entry_dict in json.load(open(sql_instruction_row_list_entry_path))
        ]
        if sample_count is None:
            sample_count = len(sql_instruction_row_list_entry_list)
        else:
            assert self.output_dir.endswith(str(sample_count))
        entry_list: list[Mapping[str, Any]] = []
        sql_instruction_row_list_entry_hash_to_index_dict: dict[int, int] = {}
        # endregion
        # region Construct entry_list
        for (
            sql_instruction_row_list_entry_index,
            sql_instruction_row_list_entry,
        ) in enumerate(sql_instruction_row_list_entry_list):
            generation_info = sql_instruction_row_list_entry.sql_instruction_entry.sql_entry.generation_info_list[
                -1
            ]
            sql = generation_info.sql
            skill_list = generation_info.skill_list
            table_name = generation_info.table_name
            column_info_list = generation_info.column_info_list
            instruction = (
                sql_instruction_row_list_entry.sql_instruction_entry.instruction_list[
                    -1
                ]
            )
            validation_result = sql_instruction_row_list_entry.validation_result_list[
                -1
            ]
            row_list = validation_result.processed_row_list
            sql_execution_result = validation_result.sql_execution_result
            assert sql_execution_result is not None  # Type narrowing
            answer_direct = sql_execution_result.answer_direct
            answer_md5 = sql_execution_result.executed_sql_table_md5
            sql_instruction_row_list_entry_hash = hash(sql_instruction_row_list_entry)
            entry_list.append(
                {
                    "answer_info": {
                        "direct": answer_direct,
                        "md5": answer_md5,
                        "sql": sql,
                    },
                    "table_info": {
                        "name": table_name,
                        "column_info_list": [
                            column_info.model_dump() for column_info in column_info_list
                        ],
                        "row_list": row_list,
                    },
                    "instruction": instruction,
                    "skill_list": skill_list,
                    "sql_instruction_row_list_entry_hash": sql_instruction_row_list_entry_hash,
                }
            )
            sql_instruction_row_list_entry_hash_to_index_dict[
                sql_instruction_row_list_entry_hash
            ] = sql_instruction_row_list_entry_index
        # endregion
        # region Shuffle the entry_list and record the index_dict
        random.shuffle(entry_list)
        entry_list = entry_list[:sample_count]
        index_dict: dict[int, int] = {}
        for entry_index, entry in enumerate(entry_list):
            sql_instruction_row_list_entry_index = (
                sql_instruction_row_list_entry_hash_to_index_dict[
                    entry["sql_instruction_row_list_entry_hash"]
                ]
            )
            index_dict[entry_index] = sql_instruction_row_list_entry_index
        # endregion
        # region Construct dataset_info
        dataset_info = DatasetInfo(
            sql_instruction_row_list_entry_path=sql_instruction_row_list_entry_path,
            sql_instruction_row_list_entry_path_length=len(
                sql_instruction_row_list_entry_list
            ),
            sample_count=sample_count,
            random_seed=self.random_seed,
            output_dir=self.output_dir,
            created_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            index_dict=index_dict,
        )
        # endregion
        # region Dump entry_list and dataset_info
        output_path_dict = self._get_output_path_dict()
        json.dump(
            {entry_index: entry for entry_index, entry in enumerate(entry_list)},
            open(output_path_dict["entry_dict_output_path"], "w"),  # noqa
            indent=2,
        )
        json.dump(
            dataset_info.model_dump(),
            open(output_path_dict["dataset_info_output_path"], "w"),  # noqa
            indent=2,
        )
        # endregion

    def validate(self) -> None:
        pseudo_db_bench = PseudoDBBench()
        entry_dict: dict[str, Any] = json.load(
            open(self._get_output_path_dict()["entry_dict_output_path"])
        )
        for entry_index, entry in entry_dict.items():
            # region Prepare dataset_item and database
            dataset_item = DBBench._construct_dataset_item(entry)  # noqa
            init_sql = DBBench._build_init_sql(dataset_item)  # noqa
            pseudo_db_bench.container.execute(init_sql)
            # endregion
            # region Execute sql and validate the answer
            sql_execution_result = pseudo_db_bench.container.execute(
                dataset_item.answer_info.ground_truth_sql, dataset_item.database_name
            )
            pseudo_db_bench.current_dataset_item = dataset_item
            answer_dict = DBBench._get_task_output(  # noqa
                pseudo_db_bench,  # type: ignore[arg-type]
                sql_execution_result,
            )
            agent_answer = answer_dict["answer"]
            match dataset_item.answer_info.answer_type:
                case AnswerType.MD5:
                    correct_flag = agent_answer == dataset_item.answer_info.answer_md5
                case AnswerType.DIRECT:
                    ground_truth = dataset_item.answer_info.answer_direct
                    assert ground_truth is not None
                    correct_flag = DirectTypeAnswerValidator.validate(
                        agent_answer, ground_truth
                    )
                case _:
                    raise NotImplementedError()
            # endregion
            # region Clean up, log progress
            pseudo_db_bench.container.execute(
                f"drop database `{dataset_item.database_name}`"  # noqa
            )
            if correct_flag:
                self.logger.info(
                    f"sample_index: {entry_index:<3}. "
                    f"answer_type: {dataset_item.answer_info.answer_type:<6}. "
                    f"Validation passed."
                )
            else:
                self.logger.error(
                    f"sample_index: {entry_index:<3}. "
                    f"answer_type: {dataset_item.answer_info.answer_type:<6}. "
                    f"Validation failed."
                )
            # endregion


def main() -> None:
    entry_factory = EntryFactory(
        row_list_factory_output_dir="data/v0303/db_bench/raw/row_list_factory/v0316",
        output_dir="data/v0303/db_bench/processed/v0317_first500",
        log_file_path="./outputs/data/v0303/db_bench/entry_factory.log",
        random_seed=0,
    )
    entry_factory.random_order_construct(sample_count=500)
    # entry_factory.validate()


if __name__ == "__main__":
    main()
