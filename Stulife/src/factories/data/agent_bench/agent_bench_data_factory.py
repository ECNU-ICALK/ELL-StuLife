import json
import os
from typing import Any, Optional

from src.tasks.instance.os_interaction.utility import CommandName


class AgentBenchDataFactory:
    @staticmethod
    def format_db_bench_data(
        original_dev_data_path: str, original_standard_data_path: str, output_path: str
    ) -> None:
        dev_list = [
            json.loads(line) for line in open(original_dev_data_path).readlines()
        ]
        standard_list = [
            json.loads(line) for line in open(original_standard_data_path).readlines()
        ]
        result: dict[int, dict[str, Any]] = {}
        for data in dev_list + standard_list:
            result[len(result)] = data
        json.dump(result, open(output_path, "w"), indent=2)

    @staticmethod
    def format_os_interaction_data(
        original_data_path: str, original_scripts_dir_path: str, output_path: str
    ) -> None:
        def load_script(
            script_obj: Optional[str | dict[str, str]]
        ) -> dict[str, CommandName | str]:
            if script_obj is None:
                raise ValueError()
                # return None
            if type(script_obj) is str:
                return {"command_name": CommandName.BASH, "script": script_obj}
            assert isinstance(script_obj, dict)
            if "language" not in script_obj:
                language = "bash"
            else:
                language = script_obj["language"]
            if language == "c++":
                language = "cpp"
            command_name = CommandName(language)
            if "file" in script_obj:
                with open(
                    os.path.join(original_scripts_dir_path, script_obj["file"])
                ) as f:
                    script = f.read()
                return {"command_name": command_name, "script": script}
            elif "code" in script_obj:
                return {"command_name": command_name, "script": script_obj["code"]}
            else:
                raise ValueError("Invalid Script Object")

        agent_bench_data: list[dict[str, Any]] = json.load(open(original_data_path))
        processed_data: dict[str, dict[str, Any]] = {}
        for item in agent_bench_data:
            description = item["description"]
            initialization_information_list: list[dict[str, str | CommandName]] = []
            if "create" in item.keys():
                if "image" in item["create"]:
                    image = item["create"]["image"]
                else:
                    image = "local-os/default"
                if "init" in item["create"]:
                    if type(item["create"]["init"]) is not list:
                        initialization_information_list = [
                            load_script(item["create"]["init"])
                        ]
                    else:
                        initialization_information_list = [
                            load_script(script) for script in item["create"]["init"]
                        ]
            else:
                image = "local-os/default"
            if "start" in item:
                start_value = item["start"]
                if start_value.startswith("python3 -c '") and start_value.endswith(
                    "' &"
                ):
                    initialization_information_list.append(
                        {"command_name": CommandName.BASH, "script": start_value}
                    )
                else:
                    raise NotImplementedError()
            original_evaluation = item["evaluation"]
            if "match" in original_evaluation:
                evaluation_dict = {
                    "ground_truth": original_evaluation["match"],
                    "ground_truth_extraction_command_item": None,
                    "evaluation_command_item": load_script(
                        {
                            "language": "python",
                            "file": "check/string-match.py",
                        }
                    ),
                }
            elif "check" in original_evaluation:
                try:
                    assert type(original_evaluation["check"]) is list
                except AssertionError:
                    print("Error:", original_evaluation, "Skipping")
                    continue
                assert len(original_evaluation["check"]) == 2
                assert original_evaluation["check"][0] is None
                evaluation_dict = {
                    "ground_truth": None,
                    "ground_truth_extraction_command_item": load_script(
                        original_evaluation["example"]
                    ),
                    "evaluation_command_item": load_script(
                        original_evaluation["check"][1]
                    ),
                }
            else:
                raise ValueError("Invalid Evaluation")
            processed_data[str(len(processed_data))] = {
                "image": image,
                "description": description,
                "initialization_command_item_list": initialization_information_list,
                "evaluation_info_dict": evaluation_dict,
            }

        json.dump(processed_data, open(output_path, "w"), indent=2)  # noqa

    @staticmethod
    def format_knowledge_graph_data(
        original_dev_data_path: str, original_standard_data_path: str, output_path: str
    ) -> None:
        dev_list = json.load(open(original_dev_data_path))
        standard_list = json.load(open(original_standard_data_path))
        result: dict[int, dict[str, Any]] = {}
        for data in dev_list + standard_list:
            result[len(result)] = data
        json.dump(result, open(output_path, "w"), indent=2)  # noqa


def main() -> None:
    # region Preparation
    agent_bench_data_root_path = "/dev_data/cxd/nlp/AgentBench/data"
    project_data_root_path = "./data/"
    # endregion
    # region DBBench
    original_dev_data_path = os.path.join(
        agent_bench_data_root_path, "dbbench/dev.jsonl"  # noqa
    )
    original_standard_data_path = os.path.join(
        agent_bench_data_root_path, "dbbench/standard.jsonl"  # noqa
    )
    output_path = os.path.join(
        project_data_root_path, "db_bench/agent_bench_merged_result.json"
    )
    AgentBenchDataFactory.format_db_bench_data(
        original_dev_data_path, original_standard_data_path, output_path
    )
    # endregion
    # region OSInteraction
    original_data_path = os.path.join(
        agent_bench_data_root_path, "os_interaction/data/dev.json"
    )
    original_scripts_dir_path = os.path.join(
        agent_bench_data_root_path, "os_interaction/scripts/dev"
    )
    output_path = os.path.join(
        project_data_root_path, "os_interaction/agent_bench_merged_result.json"
    )
    AgentBenchDataFactory.format_os_interaction_data(
        original_data_path, original_scripts_dir_path, output_path
    )
    # endregion
    # region KnowledgeGraph
    # Need to copy the ontology directory to the data directory
    original_dev_data_path = os.path.join(
        agent_bench_data_root_path, "knowledgegraph/dev.json"  # noqa
    )
    original_standard_data_path = os.path.join(
        agent_bench_data_root_path, "knowledgegraph/std.json"  # noqa
    )
    output_path = os.path.join(
        project_data_root_path, "knowledge_graph/knowledge_graph_merged_result.json"
    )
    AgentBenchDataFactory.format_knowledge_graph_data(
        original_dev_data_path, original_standard_data_path, output_path
    )
    # endregion


if __name__ == "__main__":
    main()
