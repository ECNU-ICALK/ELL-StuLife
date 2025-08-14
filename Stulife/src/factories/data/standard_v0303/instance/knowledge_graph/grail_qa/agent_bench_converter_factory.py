import json
from typing import Any, Mapping
import copy

from src.factories.data.standard_v0303.instance.knowledge_graph.grail_qa.processed_entry_factory import (
    KnowledgeGraphProcessedEntryFactory,
)


class AgentBenchConverterFactory:
    def __init__(self, raw_data_path: str, processed_data_path: str):
        self.raw_data_path = raw_data_path
        self.processed_data_path = processed_data_path

    def convert(self) -> None:
        raw_data_dict: Mapping[str, Mapping[str, Any]] = json.load(
            open(self.raw_data_path)
        )
        processed_data_dict: dict[str, Mapping[str, Any]] = {}
        for key, value in raw_data_dict.items():
            processed_value = dict(copy.deepcopy(value))
            action_name_list: list[str] = []
            for action in processed_value["actions"]:
                action_name_list.append(action[: action.find("(")])
            skill_list = KnowledgeGraphProcessedEntryFactory.get_skill_list(
                action_name_list
            )
            answer_list: list[str] = []
            for a in processed_value["answer"]:
                answer_list.append(a["answer_argument"])
            answer_list.sort()
            processed_data_dict[key] = {
                "question": processed_value["question"],
                "qid": processed_value["qid"],
                "source": processed_value["source"],
                "entity_dict": processed_value["entities"],
                "s_expression": processed_value["s_expression"],
                "action_list": processed_value["actions"],
                "answer_list": answer_list,
                "skill_list": skill_list,
            }
        json.dump(processed_data_dict, open(self.processed_data_path, "w"), indent=2)


def main() -> None:
    factory = AgentBenchConverterFactory(
        raw_data_path="data/v0121/knowledge_graph/knowledge_graph_merged_result.json",
        processed_data_path="data/v0121/knowledge_graph/processed_knowledge_graph_merged_result.json",
    )
    factory.convert()


if __name__ == "__main__":
    main()
