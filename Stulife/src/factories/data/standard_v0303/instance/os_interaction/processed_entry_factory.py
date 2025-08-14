import json
import os
from typing import Sequence, Any, Mapping, Optional
import datetime
from pydantic import BaseModel

from src.factories.data.standard_v0303.instance.os_interaction.raw_entry_factory import (
    OSInteractionRawEntry,
    OSInteractionRawEntryFactory,
)
from src.factories.data.standard_v0303.utility import (
    DatasetInfo,
    ProcessedEntryFactory,
    AllInOneEntrySubclass,
)
from src.tasks.instance.os_interaction.utility import CommandName, CommandItem
from src.tasks.instance.os_interaction.task import OSInteraction


class OSInteractionProcessedEntryFactory(ProcessedEntryFactory[OSInteractionRawEntry]):
    def __init__(
        self,
        raw_entry_path: str,
        output_dir: str,
        log_file_path: str,
        random_seed: int,
        raw_entry_cls: type[OSInteractionRawEntry],
    ):
        super().__init__(
            raw_entry_path=raw_entry_path,
            output_dir=output_dir,
            log_file_path=log_file_path,
            random_seed=random_seed,
            raw_entry_cls=raw_entry_cls,
        )

    def _construct_processed_entry_from_raw_entry(
        self, raw_entry: OSInteractionRawEntry
    ) -> dict[str, Any]:
        assert raw_entry.polished_instruction_info_list is not None
        assert raw_entry.script_instruction_info_list is not None
        instruction = raw_entry.polished_instruction_info_list[-1].polished_instruction
        last_script_instruction_info = raw_entry.script_instruction_info_list[-1]
        initialization_script = last_script_instruction_info.initialization_script
        evaluation_script = last_script_instruction_info.evaluation_script
        ground_truth_script = last_script_instruction_info.ground_truth_script
        skill_list = last_script_instruction_info.skill_list
        return {
            "instruction": instruction,
            "initialization_command_item": CommandItem(
                command_name=CommandName.BASH, script=initialization_script
            ).model_dump(),
            "evaluation_info": {
                "evaluation_command_item": CommandItem(
                    command_name=CommandName.BASH, script=evaluation_script
                ).model_dump(),
                "ground_truth_command_item": CommandItem(
                    command_name=CommandName.BASH, script=ground_truth_script
                ).model_dump(),
            },
            "skill_list": skill_list,
        }

    def validate(self) -> None:
        entry_dict: dict[str, Any] = json.load(
            open(self._get_output_path_dict()["entry_dict_output_path"])
        )
        for entry_index, entry in entry_dict.items():
            dataset_item = OSInteraction._construct_dataset_item(entry)  # noqa
            script_validation_result = OSInteractionRawEntryFactory.validate_script(
                initialization_script=dataset_item.initialization_command_item.script,
                ground_truth_script=dataset_item.evaluation_info.ground_truth_command_item.script,
                evaluation_script=dataset_item.evaluation_info.evaluation_command_item.script,
                target_skill=dataset_item.skill_list[0],
                command_execution_timeout=10,  # The same as prompt
            )
            if script_validation_result.invalid_reason is None:
                self.logger.info(f"sample_index: {entry_index:<3}. Validation passed.")
            else:
                self.logger.error(
                    f"sample_index: {entry_index:<3}. Validation failed.\n"
                    f"Reason: {script_validation_result.invalid_reason}"
                )


def main() -> None:
    processed_entry_factory = OSInteractionProcessedEntryFactory(
        raw_entry_path="data/v0303/os_interaction/raw/raw_entry_factory/v0409_target_command_count_9_to_12/valid_entry_list.json",
        output_dir="data/v0303/os_interaction/processed/v0409_tcc_9_to_12_first500",
        log_file_path="./outputs/data/v0303/os_interaction/entry_factory.log",
        random_seed=0,
        raw_entry_cls=OSInteractionRawEntry,
    )
    processed_entry_factory.random_order_construct(500)
    # processed_entry_factory.validate()


if __name__ == "__main__":
    main()
