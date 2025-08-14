from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam
import random
from typing import Optional, Sequence
from typing_extensions import override
import concurrent.futures
import datetime

from src.factories.data.standard_v0303.utility import (
    AllInOneFactory,
    AllInOneEntry,
    ValidationStatus,
    TokenUsageInfo,
    ExclusiveJsonAccessUtility,
    OpenaiCompletionException,
    DataFactoryUtility,
    JSONObjectExtractionException,
    GenerationException,
)
from src.typings import LoggerConfig
from src.tasks.instance.os_interaction.task import OSInteractionSkillUtility
from src.factories.data.standard_v0303.instance.os_interaction.demonstration import (
    INSTRUCTION_SCRIPT_GENERATION_DEMONSTRATION_INFO_LIST,
)
from src.factories.data.standard_v0303.instance.os_interaction.skill_evaluator import (
    SkillEvaluator,
    SkillEvaluationResult,
)
from src.factories.data.standard_v0303.instance.os_interaction.script_evaluator import (
    ScriptEvaluator,
)


class ScriptInstructionInfo(BaseModel):
    ground_truth_script: str
    evaluation_script: str
    initialization_script: str
    instruction: str
    skill_list: Optional[Sequence[str]]
    command_count: Optional[int]
    invalid_reason: Optional[str]


class PolishedInstructionInfo(BaseModel):
    polished_instruction: str
    reason: str
    is_possible: bool
    token_usage_info: TokenUsageInfo


class PolishedInstructionInfoExtractionException(GenerationException):
    pass


class OSInteractionRawEntry(AllInOneEntry):
    script_instruction_info_list: Optional[Sequence[ScriptInstructionInfo]]
    polished_instruction_info_list: Optional[Sequence[PolishedInstructionInfo]]
    invalid_reason_list: Optional[Sequence[str]]
    token_usage_info_list: Sequence[TokenUsageInfo]
    target_command_count: int

    def get_skill_list(self) -> Optional[Sequence[str]]:
        assert self.script_instruction_info_list is not None  # Type narrowing
        return self.script_instruction_info_list[-1].skill_list

    def get_action_list(self) -> Optional[Sequence[str]]:
        assert self.script_instruction_info_list is not None  # Type narrowing
        return [self.script_instruction_info_list[-1].ground_truth_script]


class ScriptValidationResult(BaseModel):
    invalid_reason: Optional[str]
    skill_evaluation_result: Optional[SkillEvaluationResult]


class OSInteractionRawEntryFactory(AllInOneFactory[OSInteractionRawEntry]):
    def __init__(
        self,
        output_dir: str,
        log_file_path: str,
        minimum_sample_count_per_skill: int,
        minimum_total_sample_count: int,
        maximum_consecutive_failure_count: int,
        model_name: str,
        enforce_deepseek_discount_flag: bool,
        entry_subclass_cls: type[OSInteractionRawEntry],
        skill_utility_cls: type[OSInteractionSkillUtility],
        maximum_generation_count_per_skill: int,
        maximum_polish_count_per_instruction: int,
        target_command_count_list: Sequence[int],
    ):
        super().__init__(
            output_dir=output_dir,
            logger_config=LoggerConfig(
                level="INFO",
                log_file_path=log_file_path,
                logger_name="os_interaction_raw_entry_factory",
            ),
            minimum_sample_count_per_skill=minimum_sample_count_per_skill,
            minimum_total_sample_count=minimum_total_sample_count,
            maximum_consecutive_failure_count=maximum_consecutive_failure_count,
            model_name=model_name,
            enforce_deepseek_discount_flag=enforce_deepseek_discount_flag,
            entry_subclass_cls=entry_subclass_cls,
            skill_utility_cls=skill_utility_cls,
        )
        self.maximum_generation_count_per_skill = maximum_generation_count_per_skill
        self.maximum_polish_count_per_instruction = maximum_polish_count_per_instruction
        self.target_command_count_list = target_command_count_list

    @classmethod
    @override
    def _generate_candidate_skill_count_when_generating_target_skill_list(
        cls, insufficient_skill_count: int
    ) -> int:
        return 1

    @override
    def _get_skill_count_threshold(self, target_skill_count: int) -> int:
        return 1

    @staticmethod
    def _construct_demonstration_str() -> str:
        demonstration_str = ""
        for example_index, example in enumerate(
            INSTRUCTION_SCRIPT_GENERATION_DEMONSTRATION_INFO_LIST
        ):
            example_str = f"""Example {example_index + 1}:
- Instruction: {example['instruction']}
- Initialization Script: {example['initialization_script']}
- Ground Truth Script: {example['ground_truth_script']}
- Evaluation Script: {example['evaluation_script']}
"""
            demonstration_str += example_str
        demonstration_str = demonstration_str.strip()  # Remove trailing newline
        return demonstration_str

    @staticmethod
    def _construct_prompt_for_instruction_script_generation(
        target_skill: str, target_command_count: int
    ) -> str:
        # region Construct command_count_requirement
        command_count_requirement: str
        if target_command_count == 1:
            command_count_requirement = "The ground_truth_script should be simple and straightforward, using only a single command to accomplish the task."
        else:
            command_count_lower_bound = max(1, target_command_count - 1)
            command_count_upper_bound = target_command_count + 1
            command_count_requirement = f"The ground_truth_script should use about {command_count_lower_bound} to {command_count_upper_bound} commands to accomplish the task. Different commands should be connected using operators such as `|`, `&&`, or `;`."
        # endregion
        # region Construct demonstration_str
        demonstration_str = OSInteractionRawEntryFactory._construct_demonstration_str()
        # endregion
        prompt = f"""I want to generate a high-quality example for evaluating large language model (LLM) agents in an operating system environment. You will provided with a command name, and you need to generate:
- An instruction that describe the task that the LLM agent need to be accomplished in the operating system.
- An initialization bash script that setup the Ubuntu docker container environment.
- A ground truth bash script that accomplish the task.
- An evaluation bash script that check whether the task is accomplished.

1. Output Format:
    - The response must contain a JSON object encapsulated within a ```json``` code block.
    - The JSON object must contain the following keys:
        - instruction (str): A clear and concise instruction defining the task that LLM agents must achieve within the operating system. The task involves executing bash commands.
        - initialization_script (str): A valid bash command to prepare the Ubuntu Docker container environment.
        - ground_truth_script (str): A valid bash command that completes the task successfully.
        - evaluation_script (str): A valid bash command to verify task completion. This command should:
            - Return an exit code `0` if the task is successfully completed.
            - Return an exit code `1` if the task is not successfully completed.

2. Requirements:
    - The command in the initialization_script, ground_truth_script, and evaluation_script must be valid and executable in the Ubuntu Docker container. Also, both the ground_truth_script and evaluation_script should be related to the task described in the instruction.
    - Before the execution of the ground_truth_script, the execution of evaluation_script should return an exit code of `1`.
    - After the execution of the ground_truth_script, the execution of evaluation_script should return an exit code of `0`.
    - {command_count_requirement}
    - Other commands can also be included in ground_truth_script. But you have to limit the name of command in this list: {OSInteractionSkillUtility.get_all_skill_list()}.
    - The validity of generated samples will be checked by:
        - Running the initialization_script and then the ground_truth_script to ensure evaluation_script returns an exit code of `0`.
        - Running only the initialization_script (without solving the task) to ensure evaluation_script returns an exit code of `1`.
    - Design tasks to complete within 10 seconds; longer tasks will be considered invalid.
    - The task should be related to the command name `{target_skill}`. This means the command must be used in the ground_truth_script.

3. Belows are some demonstrations.
{demonstration_str}

4. Now, please generate a new example based on the above requirements. The example should be related to the command name `{target_skill}` and the ground_truth_script should use {target_command_count} commands to accomplish the task.
"""
        return prompt

    @staticmethod
    def _construct_prompt_for_instruction_polish(
        instruction: str,
        initialization_script: str,
        ground_truth_script: str,
        evaluation_script: str,
    ) -> str:
        prompt = f"""I am generating a high-quality example for evaluating large language model (LLM) agents in an operating system environment. The environment will first be initialized using the initialization+script. Then, the LLM agent will be provided with an instruction, and it is expected to generate a ground_truth_script that accomplishes the task described in the instruction. The evaluation_script will be used to check whether the task is accomplished.

Your task is to judge whether it is possible for the LLM agent to generate the bash commands that has the same effect as the ground_truth_script based on the provided instruction. If the instruction is not clear or too vague, please provide a more polished version of the instruction. The polished instruction should be clear and concise, making it easy for the LLM agent to understand the task.

1. Output Format:
    - The response must contain a JSON object encapsulated within a ```json``` code block.
    - The JSON object must include the following keys:
        - is_possible (bool): Whether it is possible for the LLM agent to generate the bash commands that has the same effect as the ground_truth_script based on the provided instruction.
        - reason (str): The reason for the judgement.
        - polished_instruction (str): The polished instruction. If the instruction is good enough, output an empty string here.
        
2. Basic Requirements:
    - The polished instruction should be more clear and concise than the original instruction.
    - You can output other content, but you must include a JSON object with the correct format in the response.

3. Below are some demonstrations of the instruction and their corresponding initialization_script, ground_truth_script, and evaluation_script:
{OSInteractionRawEntryFactory._construct_demonstration_str()}

4. Now, please judge whether the instruction is clear and concise enough for the LLM agent to understand the task. If it is not, please provide a more polished version of the instruction.
- Instruction: {instruction}
- Initialization Script: {initialization_script}
- Ground Truth Script: {ground_truth_script}
- Evaluation Script: {evaluation_script}
"""
        return prompt

    @staticmethod
    def validate_script(
        initialization_script: str,
        ground_truth_script: str,
        evaluation_script: str,
        target_skill: str,
        command_execution_timeout: int,
    ) -> ScriptValidationResult:
        # region Get skill_evaluation_result
        try:
            skill_evaluation_result = SkillEvaluator.evaluate(ground_truth_script)
        except Exception as e:
            return ScriptValidationResult(
                invalid_reason=f"Cannot parse the script. Reason: {str(e)}",
                skill_evaluation_result=None,
            )
        # endregion
        # region Validate the script
        script_evaluator = ScriptEvaluator(
            initialization_script=initialization_script,
            ground_truth_script=ground_truth_script,
            evaluation_script=evaluation_script,
            command_execution_timeout=command_execution_timeout,
        )
        script_invalid_reason = script_evaluator.evaluate()
        if script_invalid_reason is not None:
            return ScriptValidationResult(
                invalid_reason=script_invalid_reason,
                skill_evaluation_result=skill_evaluation_result,
            )
        # endregion
        # region Validate the skill
        if target_skill not in skill_evaluation_result.skill_set:
            return ScriptValidationResult(
                invalid_reason=f"The skill {target_skill} is not used in the ground_truth_script.",
                skill_evaluation_result=skill_evaluation_result,
            )
        # endregion
        return ScriptValidationResult(
            invalid_reason=None,
            skill_evaluation_result=skill_evaluation_result,
        )

    def _polish_instruction(
        self,
        instruction_to_be_polished: str,
        initialization_script: str,
        ground_truth_script: str,
        evaluation_script: str,
    ) -> PolishedInstructionInfo:
        prompt = OSInteractionRawEntryFactory._construct_prompt_for_instruction_polish(
            instruction=instruction_to_be_polished,
            initialization_script=initialization_script,
            ground_truth_script=ground_truth_script,
            evaluation_script=evaluation_script,
        )
        chat_completion, token_usage_info = (
            DataFactoryUtility.get_single_chat_completion(
                self.client,
                self.model_name,
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                self.token_usage_info_list_path,
                log_prefix="Instruction polish: ",
            )
        )
        content = chat_completion.choices[0].message.content
        assert content is not None  # Type narrowing
        try:
            polished_instruction_info_dict = (
                DataFactoryUtility.extract_json_object_from_chat_completion_content(
                    content,
                    required_key_list=["is_possible", "reason", "polished_instruction"],
                )
            )
        except JSONObjectExtractionException as e:
            error_message = f"Instruction polish: {str(e)}"
            self.logger.error(error_message)
            raise PolishedInstructionInfoExtractionException(error_message) from e
        if not polished_instruction_info_dict["is_possible"]:
            if (
                not isinstance(
                    polished_instruction_info_dict["polished_instruction"], str
                )
                or polished_instruction_info_dict["polished_instruction"].strip() == ""
            ):
                raise PolishedInstructionInfoExtractionException(
                    "The original instruction is not good enough, but the polished instruction is empty."
                )
        else:
            polished_instruction_info_dict["polished_instruction"] = (
                instruction_to_be_polished
            )
        return PolishedInstructionInfo(
            polished_instruction=polished_instruction_info_dict["polished_instruction"],
            reason=polished_instruction_info_dict["reason"],
            is_possible=polished_instruction_info_dict["is_possible"],
            token_usage_info=token_usage_info,
        )

    def _generate_from_target_skill_list(
        self, target_skill_list: Sequence[str]
    ) -> OSInteractionRawEntry:
        # region Generate instruction, scripts
        # region Preparation
        # I will not validate the command count
        target_command_count = random.choice(self.target_command_count_list)
        target_skill = target_skill_list[0]
        message_list: list[ChatCompletionMessageParam] = [
            {
                "role": "user",
                "content": OSInteractionRawEntryFactory._construct_prompt_for_instruction_script_generation(
                    target_skill=target_skill, target_command_count=target_command_count
                ),
            }
        ]
        token_usage_info_list: list[TokenUsageInfo] = []
        invalid_reason_list: list[str] = []
        script_instruction_info_list: list[ScriptInstructionInfo] = []
        # endregion
        for script_instruction_generation_round_index in range(
            self.maximum_generation_count_per_skill
        ):
            # region Generation
            try:
                chat_completion, token_usage_info = (
                    DataFactoryUtility.get_single_chat_completion(
                        self.client,
                        self.model_name,
                        message_list,
                        self.token_usage_info_list_path,
                        log_prefix="Instruction Generation: ",
                    )
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to extract useful chat_completion. {script_instruction_generation_round_index=}"
                )
                raise OpenaiCompletionException(str(e)) from e
            token_usage_info_list.append(token_usage_info)
            # endregion
            # region Maintain message_list
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
            # region Extract instruction, scripts
            try:
                script_instruction_info_entry_dict = (
                    DataFactoryUtility.extract_json_object_from_chat_completion_content(
                        content,
                        [
                            "instruction",
                            "initialization_script",
                            "ground_truth_script",
                            "evaluation_script",
                        ],
                    )
                )
            except JSONObjectExtractionException as e:
                invalid_reason = str(e)
                self.logger.error(
                    f"Failed to extract useful json object in script_instruction_generation. "
                    f"{script_instruction_generation_round_index=} ."
                    f"{invalid_reason=}"
                )
                invalid_reason_list.append(
                    f"Reason from the script_instruction generation process: {invalid_reason}"
                )
                message_list.append(
                    {
                        "role": "user",
                        "content": f"{invalid_reason} Please try again.",
                    }
                )
                continue
            # endregion
            # region Validate the script
            # region Get validation result
            initialization_script = script_instruction_info_entry_dict[
                "initialization_script"
            ]
            ground_truth_script = script_instruction_info_entry_dict[
                "ground_truth_script"
            ]
            evaluation_script = script_instruction_info_entry_dict["evaluation_script"]
            # The command_execution_timeout in the prompt is 10.
            # Here, I set it to 5 to make the validation process stricter.
            script_validation_result = OSInteractionRawEntryFactory.validate_script(
                initialization_script=initialization_script,
                ground_truth_script=ground_truth_script,
                evaluation_script=evaluation_script,
                target_skill=target_skill,
                command_execution_timeout=5,
            )
            if script_validation_result.skill_evaluation_result is None:
                actual_command_count = None
            else:
                actual_command_count = (
                    script_validation_result.skill_evaluation_result.command_count
                )
            # endregion
            if script_validation_result.invalid_reason is not None:
                self.logger.error(
                    f"Script validation failed in script_instruction_generation.\n"
                    f"round_index          : {script_instruction_generation_round_index}\n"
                    f"target_skill         : {target_skill}\n"
                    f"initialization_script: {initialization_script}\n"
                    f"target_command_count : {target_command_count}\n"
                    f"ground_truth_script  : {ground_truth_script}\n"
                    f"evaluation_script    : {evaluation_script} \n"
                    f"invalid_reason       : {script_validation_result.invalid_reason}\n"
                    f"actual_command_count : {actual_command_count}\n"
                )
                invalid_reason = script_validation_result.invalid_reason
                invalid_reason_list.append(
                    f"Reason from the script_instruction generation process: "
                    f"<SCRIPT_INSTRUCTION_INFO_INDEX_START>"
                    f"{len(script_instruction_info_list)}"
                    f"<SCRIPT_INSTRUCTION_INFO_INDEX_END>"
                )
                message_list.append(
                    {
                        "role": "user",
                        "content": f"{invalid_reason} Please try again.",
                    }
                )
                script_instruction_info_list.append(
                    ScriptInstructionInfo(
                        ground_truth_script=ground_truth_script,
                        evaluation_script=evaluation_script,
                        initialization_script=initialization_script,
                        instruction=script_instruction_info_entry_dict["instruction"],
                        skill_list=None,
                        command_count=actual_command_count,
                        invalid_reason=invalid_reason,
                    )
                )
                continue
            else:
                # Type narrowing
                assert script_validation_result.skill_evaluation_result is not None
                script_instruction_info_list.append(
                    ScriptInstructionInfo(
                        ground_truth_script=ground_truth_script,
                        evaluation_script=evaluation_script,
                        initialization_script=initialization_script,
                        instruction=script_instruction_info_entry_dict["instruction"],
                        skill_list=sorted(
                            list(
                                script_validation_result.skill_evaluation_result.skill_set
                            )
                        ),
                        command_count=actual_command_count,
                        invalid_reason=None,
                    )
                )
                break
            # endregion
        if (
            len(script_instruction_info_list) == 0
            or script_instruction_info_list[-1].invalid_reason is not None
        ):
            return OSInteractionRawEntry(
                script_instruction_info_list=(
                    script_instruction_info_list
                    if len(script_instruction_info_list) > 0
                    else None
                ),
                polished_instruction_info_list=None,
                invalid_reason_list=(
                    invalid_reason_list if len(invalid_reason_list) > 0 else None
                ),
                token_usage_info_list=token_usage_info_list,
                target_command_count=target_command_count,
                validation_status=ValidationStatus.CANNOT_BE_REUSED,
                target_skill_list=target_skill_list,
            )
        # endregion
        # region Polish instruction
        instruction_to_be_polished = script_instruction_info_list[-1].instruction
        polished_instruction_info_list: list[PolishedInstructionInfo] = []
        for instruction_polish_round_index in range(
            self.maximum_polish_count_per_instruction
        ):
            try:
                polished_instruction_info = self._polish_instruction(
                    instruction_to_be_polished=instruction_to_be_polished,
                    initialization_script=script_instruction_info_list[
                        -1
                    ].initialization_script,
                    ground_truth_script=script_instruction_info_list[
                        -1
                    ].ground_truth_script,
                    evaluation_script=script_instruction_info_list[
                        -1
                    ].evaluation_script,
                )
            except OpenaiCompletionException as e:
                error_message = (
                    "Instruction Polish: Cannot get polished_instruction_info."
                )
                self.logger.error(error_message)
                raise OpenaiCompletionException(error_message) from e
            except PolishedInstructionInfoExtractionException as e:
                error_message = str(e)
                self.logger.error(error_message)
                continue
            polished_instruction_info_list.append(polished_instruction_info)
            if not polished_instruction_info.is_possible:
                instruction_to_be_polished = (
                    polished_instruction_info.polished_instruction
                )
            else:
                return OSInteractionRawEntry(
                    script_instruction_info_list=script_instruction_info_list,
                    polished_instruction_info_list=polished_instruction_info_list,
                    invalid_reason_list=(
                        invalid_reason_list if len(invalid_reason_list) > 0 else None
                    ),
                    token_usage_info_list=token_usage_info_list,
                    target_command_count=target_command_count,
                    validation_status=ValidationStatus.VALID,
                    target_skill_list=target_skill_list,
                )
        # endregion
        return OSInteractionRawEntry(
            script_instruction_info_list=script_instruction_info_list,
            polished_instruction_info_list=polished_instruction_info_list,
            invalid_reason_list=(
                invalid_reason_list if len(invalid_reason_list) > 0 else None
            ),
            token_usage_info_list=token_usage_info_list,
            target_command_count=target_command_count,
            validation_status=ValidationStatus.CANNOT_BE_REUSED,
            target_skill_list=target_skill_list,
        )


def main() -> None:
    for target_command_count_list in ([5, 6, 7, 8], [9, 10, 11, 12]):

        def worker() -> None:
            raw_entry_factory = OSInteractionRawEntryFactory(
                output_dir=f"./data/v0303/os_interaction/raw/raw_entry_factory/v0409{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                log_file_path="./outputs/data/v0303/os_interaction/os_interaction_factory.log",
                minimum_sample_count_per_skill=15,
                minimum_total_sample_count=500,
                maximum_consecutive_failure_count=20,
                model_name="deepseek-reasoner",
                enforce_deepseek_discount_flag=True,
                entry_subclass_cls=OSInteractionRawEntry,
                skill_utility_cls=OSInteractionSkillUtility,
                maximum_generation_count_per_skill=5,
                maximum_polish_count_per_instruction=5,
                target_command_count_list=target_command_count_list,
            )
            raw_entry_factory.construct()

        thread_count = 32
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_count
        ) as executor:
            futures = [executor.submit(worker) for _ in range(thread_count)]
            for future in concurrent.futures.as_completed(futures):
                # This will re‑raise any exceptions that occurred in the worker
                future.result()


if __name__ == "__main__":
    main()
