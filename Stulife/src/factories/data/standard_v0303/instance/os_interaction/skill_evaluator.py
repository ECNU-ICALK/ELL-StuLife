import bashlex  # type: ignore[import-untyped]
import bashlex.ast  # type: ignore[import-untyped]
from pydantic import BaseModel

from src.tasks.instance.os_interaction.task import OSInteractionSkillUtility


class SkillEvaluationResult(BaseModel):
    skill_set: set[str]
    command_count: int


class SkillEvaluator:
    @staticmethod
    def evaluate_node_list(
        node_list: list[bashlex.ast.node],
    ) -> tuple[set[str], list[bashlex.ast.node]]:
        skill_set: set[str] = set()
        command_node_list: list[bashlex.ast.node] = []
        for node in node_list:
            if node.kind in ["list", "pipeline", "while"]:
                _skill_set, _command_node_list = SkillEvaluator.evaluate_node_list(
                    node.parts
                )
                skill_set.update(_skill_set)
                command_node_list.extend(_command_node_list)
            elif node.kind == "compound":
                _skill_set, _command_node_list = SkillEvaluator.evaluate_node_list(
                    node.list
                )
                skill_set.update(_skill_set)
                command_node_list.extend(_command_node_list)
            elif node.kind == "command":
                command = node.parts[0].word if node.parts else None
                if command in OSInteractionSkillUtility.get_all_skill_list():
                    skill_set.add(command)
                    command_node_list.append(node)
                else:
                    # print(command)
                    pass
            elif node.kind in [
                "operator",
                "redirect",
                "pipe",
                "reservedword",
                "if",
                "for",
            ]:
                # Skip reserved or operator nodes
                continue
            else:
                raise NotImplementedError(f"Unsupported node kind: {node.kind}")
        return skill_set, command_node_list

    @staticmethod
    def evaluate(script: str) -> SkillEvaluationResult:
        node_list: list[bashlex.ast.node] = bashlex.parse(script)
        skill_set, command_node_list = SkillEvaluator.evaluate_node_list(node_list)
        return SkillEvaluationResult(
            skill_set=skill_set,
            command_count=len(command_node_list),
        )
