import json
import random
import re
from typing import Mapping, Sequence, Any
from pydantic import BaseModel
import os
import datetime

from src.factories.data.standard_v0303.instance.knowledge_graph.grail_qa.action_info_factory import (
    Function,
    ActionInfoEntry,
)
from src.tasks.instance.knowledge_graph.task import KnowledgeGraphDatasetItem
from src.utils import SingletonLogger
from src.typings import LoggerConfig


class KnowledgeGraphDatasetInfo(BaseModel):
    action_info_entry_list_path: str
    total_valid_action_info_entry_count: int
    target_trajectory_length_to_sample_count: Mapping[
        int, int
    ]  # trajectory_length -> sample_count
    actual_sample_info: Mapping[
        int, Mapping[Function, Sequence[int]]
    ]  # trajectory_length -> function_name -> list[sample_index]
    random_seed: int
    output_dir: str
    created_time: str
    index_dict: Mapping[int, int]  # sample_index -> qid


class KnowledgeGraphProcessedEntryFactory:
    def __init__(
        self,
        action_info_entry_list_path: str,
        output_dir: str,
        log_file_path: str,
        random_seed: int,
        target_trajectory_length_to_sample_count: Mapping[
            int, int
        ],  # trajectory_length -> sample_count
    ):
        assert output_dir.endswith("/")
        self.output_dir = output_dir
        assert "<<BRIEF_SAMPLE_INFO_STR>>" in output_dir.split("/")[-2]
        self.logger = SingletonLogger.get_instance(
            LoggerConfig(
                level="INFO",
                log_file_path=log_file_path,
                logger_name="knowledge_graph_standard_data_factory",
            )
        )
        self.action_info_entry_list_path = action_info_entry_list_path
        action_info_entry_list = [
            ActionInfoEntry.model_validate(entry_dict)
            for entry_dict in json.load(open(self.action_info_entry_list_path, "r"))
        ]
        self.random_seed = random_seed
        random.seed(self.random_seed)
        random.shuffle(action_info_entry_list)
        self.action_info_entry_list: Sequence[ActionInfoEntry] = action_info_entry_list
        self.target_trajectory_length_to_sample_count = {
            key: target_trajectory_length_to_sample_count[key]
            for key in sorted(target_trajectory_length_to_sample_count.keys())
        }

    @staticmethod
    def _get_output_path_dict(output_dir: str) -> Mapping[str, str]:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return {
            "entry_dict_output_path": os.path.join(output_dir, "entry_dict.json"),
            "dataset_info_output_path": os.path.join(output_dir, "dataset_info.json"),
        }

    @staticmethod
    def _is_valid_action_info_entry(entry: ActionInfoEntry) -> bool:
        if entry.action_info is None:
            return False
        for agent_action_info in entry.action_info.agent_action_info_list:
            if agent_action_info.error_message_list is not None:
                return False
        for entity_name in entry.action_info.entity_dict.keys():
            if not re.fullmatch(r"[a-zA-Z0-9 _-]+", entity_name):
                return False
        return True

    def _select_entry(
        self, target_trajectory_length: int, target_sample_count: int
    ) -> Mapping[Function, Sequence[ActionInfoEntry]]:
        function_to_candidate_entry_dict: Mapping[Function, list[ActionInfoEntry]] = {
            function: [] for function in Function
        }
        for entry in self.action_info_entry_list:
            if not KnowledgeGraphProcessedEntryFactory._is_valid_action_info_entry(
                entry
            ):
                continue
            assert entry.action_info is not None
            sample_trajectory_length = len(entry.action_info.agent_action_info_list)
            if sample_trajectory_length != target_trajectory_length:
                continue
            function_to_candidate_entry_dict[entry.grail_qa_entry.function].append(
                entry
            )
        return_entry_dict: Mapping[Function, list[ActionInfoEntry]] = {
            function: [] for function in Function
        }
        selected_sample_count = 0
        while True:
            no_candidate_entry_flag = True
            for function in Function:
                candidate_entry_list = function_to_candidate_entry_dict[function]
                if len(candidate_entry_list) == 0:
                    continue
                no_candidate_entry_flag = False
                selected_entry = candidate_entry_list.pop(0)
                return_entry_dict[function].append(selected_entry)
                selected_sample_count += 1
                if selected_sample_count == target_sample_count:
                    break
            if no_candidate_entry_flag or selected_sample_count == target_sample_count:
                break
        return return_entry_dict

    @staticmethod
    def get_skill_list(action_name_list: Sequence[str]) -> Sequence[str]:
        skill_set: set[str] = set()
        for action_name in action_name_list:
            match action_name:
                case "get_relations" | "get_attributes":
                    pass
                case "get_neighbors" | "intersection" | "argmax" | "argmin" | "count":
                    skill_set.add(action_name)
                case _:
                    raise ValueError()
        skill_list = sorted(list(skill_set))
        return skill_list

    def construct(self) -> None:
        # region Construct selected_entry_dict
        selected_entry_dict: dict[int, Mapping[Function, Sequence[ActionInfoEntry]]] = {
            trajectory_length: {function: [] for function in Function}
            for trajectory_length in self.target_trajectory_length_to_sample_count.keys()
        }
        for (
            trajectory_length,
            sample_count,
        ) in self.target_trajectory_length_to_sample_count.items():
            selected_entry_dict[trajectory_length] = self._select_entry(
                target_trajectory_length=trajectory_length,
                target_sample_count=sample_count,
            )
        # endregion
        # region Construct selected_entry_list
        selected_entry_list: list[ActionInfoEntry] = []
        for (
            trajectory_length,
            function_to_entry_list_dict,
        ) in selected_entry_dict.items():
            for function, entry_list in function_to_entry_list_dict.items():
                selected_entry_list.extend(entry_list)
        random.seed(self.random_seed)
        random.shuffle(selected_entry_list)
        qid_to_sample_index_dict: dict[int, int] = {}
        for sample_index, entry in enumerate(selected_entry_list):
            qid_to_sample_index_dict[entry.grail_qa_entry.qid] = sample_index
        # endregion
        # region Construct dataset_info
        total_valid_action_info_entry_count = 0
        for entry in selected_entry_list:
            if KnowledgeGraphProcessedEntryFactory._is_valid_action_info_entry(entry):
                total_valid_action_info_entry_count += 1
        actual_sample_info = {
            trajectory_length: {
                function: [
                    qid_to_sample_index_dict[entry.grail_qa_entry.qid]
                    for entry in entry_list
                ]
                for function, entry_list in function_to_entry_list_dict.items()
            }
            for trajectory_length, function_to_entry_list_dict in selected_entry_dict.items()
        }
        brief_sample_info_str = ""
        for (
            trajectory_length,
            function_to_entry_list_dict,
        ) in selected_entry_dict.items():
            sample_count = len(
                [
                    entry
                    for entry_list in function_to_entry_list_dict.values()
                    for entry in entry_list
                ]
            )
            brief_sample_info_str += f"tl{trajectory_length}sc{sample_count}_"
        brief_sample_info_str = brief_sample_info_str[:-1]
        output_dir = self.output_dir.replace(
            "<<BRIEF_SAMPLE_INFO_STR>>", brief_sample_info_str
        )
        dataset_info = KnowledgeGraphDatasetInfo(
            action_info_entry_list_path=self.action_info_entry_list_path,
            total_valid_action_info_entry_count=total_valid_action_info_entry_count,
            target_trajectory_length_to_sample_count=self.target_trajectory_length_to_sample_count,
            actual_sample_info=actual_sample_info,
            random_seed=self.random_seed,
            output_dir=output_dir,
            created_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            index_dict={
                sample_index: entry.grail_qa_entry.qid
                for sample_index, entry in enumerate(selected_entry_list)
            },
        )
        # endregion
        # region Convert selected_entry_list to processed_entry_list
        processed_entry_dict: dict[str, dict[str, Any]] = {}
        for entry in selected_entry_list:
            assert entry.action_info is not None
            assert entry.action_info.s_expression_execution_result is not None
            # region Construct action_list
            action_list: list[str] = []
            for agent_action_info in entry.action_info.agent_action_info_list:
                argument_str = "("
                for argument in agent_action_info.argument_list:
                    argument_str += f"{argument},"
                argument_str = argument_str[:-1] + ")"
                action_list.append(f"{agent_action_info.action_name}{argument_str}")
            # endregion
            # region Construct skill_list
            action_name_list: list[str] = []
            for agent_action_info in entry.action_info.agent_action_info_list:
                action_name_list.append(agent_action_info.action_name)
            skill_list = KnowledgeGraphProcessedEntryFactory.get_skill_list(
                action_name_list
            )
            # endregion
            processed_entry_dict[str(len(processed_entry_dict))] = {
                "question": entry.grail_qa_entry.question,
                "qid": f"{entry.grail_qa_entry.qid}_grailqa",
                "source": "grailqa",
                "entity_dict": entry.action_info.entity_dict,
                "s_expression": entry.action_info.processed_s_expression,
                "action_list": action_list,
                "answer_list": entry.action_info.s_expression_execution_result.processed,
                "skill_list": skill_list,
            }
        # endregion
        output_path_dict = self._get_output_path_dict(output_dir)
        json.dump(
            processed_entry_dict,
            open(output_path_dict["entry_dict_output_path"], "w"),  # noqa
            indent=2,
        )
        json.dump(
            dataset_info.model_dump(),
            open(output_path_dict["dataset_info_output_path"], "w"),  # noqa
            indent=2,
        )


def main() -> None:
    for target_trajectory_length in list(range(2, 10)):
        processed_entry_factory = KnowledgeGraphProcessedEntryFactory(
            action_info_entry_list_path="data/v0303/knowledge_graph/raw/action_info_factory/v0415/action_info_entry_list.json",
            output_dir="data/v0303/knowledge_graph/processed/grailqa/v0417_<<BRIEF_SAMPLE_INFO_STR>>/",
            log_file_path="./outputs/data/v0303/os_interaction/action_info_factory.log",
            random_seed=0,
            target_trajectory_length_to_sample_count={target_trajectory_length: 100},
        )
        processed_entry_factory.construct()


if __name__ == "__main__":
    main()
