from typing import Optional

from src.tasks.instance.os_interaction.container import OSInteractionContainer
from src.tasks.instance.os_interaction.utility import CommandItem, CommandName


class ScriptEvaluator:
    def __init__(
        self,
        initialization_script: str,
        ground_truth_script: str,
        evaluation_script: str,
        command_execution_timeout: int,
    ):
        self.container: OSInteractionContainer = OSInteractionContainer(
            command_execution_timeout=command_execution_timeout
        )
        self.command_execution_timeout = command_execution_timeout
        self.ground_truth_script = ground_truth_script
        self.evaluation_script = evaluation_script
        self.initialization_script = initialization_script
        self.initialization_error_message: Optional[str] = None

    def _initialize_container(self) -> None:
        self.container.terminate()
        self.container = OSInteractionContainer(
            command_execution_timeout=self.command_execution_timeout
        )
        execution_result = self.container.execute_independent(
            CommandItem(
                command_name=CommandName.BASH, script=self.initialization_script
            )
        )
        if execution_result.timeout_flag:
            self.initialization_error_message = (
                f"Initialization script execution time exceeds {self.container.timeout_sec}.\n"
                f"Execution output was {execution_result.output}"
            )
        elif execution_result.exit_code != 0:
            self.initialization_error_message = (
                f"Initialization script failed with exit code {execution_result.exit_code}.\n"
                f"Execution output was:\n{execution_result.output}"
            )

    def evaluate(self) -> Optional[str]:
        self._initialize_container()
        # region Handle initialization_script
        if self.initialization_error_message:
            return self.initialization_error_message
        # endregion
        # region Handle trivial case
        assert self.container is not None
        execution_result = self.container.execute_independent(
            CommandItem(command_name=CommandName.BASH, script=self.evaluation_script)
        )
        if execution_result.exit_code == 0:
            return """The evaluation_script returns code 0 without the execution of the ground_truth_script.
The example is too trivial. Remember: 
- Before the execution of the ground_truth_script, the execution of evaluation_script should return an exit code of `1`.
- After the execution of the ground_truth_script, the execution of evaluation_script should return an exit code of `0`.
"""
        # endregion
        # region Handle ground_truth_script
        self._initialize_container()
        # region Get ground_truth_error_message
        ground_truth_error_message: Optional[str] = None
        execution_result = self.container.execute_independent(
            CommandItem(command_name=CommandName.BASH, script=self.ground_truth_script)
        )
        if execution_result.timeout_flag:
            ground_truth_error_message = (
                f"ground_truth_script execution time exceeds {self.container.timeout_sec}.\n"
                f"Execution output was {execution_result.output}"
            )
        elif execution_result.exit_code != 0:
            ground_truth_error_message = (
                f"ground_truth_script failed with exit code {execution_result.exit_code}.\n"
                f"Execution output was: {execution_result.output}"
            )
        # endregion
        execution_result = self.container.execute_independent(
            CommandItem(command_name=CommandName.BASH, script=self.evaluation_script)
        )
        self.container.terminate()
        if execution_result.timeout_flag:
            validation_error_message = (
                f"evaluation_script execution time exceeds {self.container.timeout_sec}.\n"
                f"Execution output was {execution_result.output}"
            )
            if ground_truth_error_message is not None:
                return f"{ground_truth_error_message}\n{validation_error_message}"
            else:
                return validation_error_message
        elif execution_result.exit_code != 0:
            validation_error_message = (
                f"evaluation_script failed with exit code {execution_result.exit_code}.\n"
                f"Execution output was: {execution_result.output}\n"
                f"Remember: After the execution of the ground_truth_script, the execution of evaluation_script should return an exit code of `0`."
            )
            if ground_truth_error_message is not None:
                return f"{ground_truth_error_message}\n{validation_error_message}"
            else:
                return validation_error_message
        else:
            return None
        # endregion
