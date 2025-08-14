import json
from pydantic import BaseModel
from enum import StrEnum
from typing import Optional, Any, Sequence, Mapping
from tqdm import tqdm
import os
import copy

from src.tasks.instance.knowledge_graph.api import KnowledgeGraphAPI
from src.tasks.instance.knowledge_graph.utils.semantic_parser_util import (
    SemanticParserUtil,
)
from src.tasks.instance.knowledge_graph.utils.logic_form_util import LogicFormUtil
from src.tasks.instance.knowledge_graph.utils.sparql_executor import SparqlExecutor
from src.utils import SingletonLogger
from src.typings import LoggerConfig
from src.factories.data.standard_v0303.instance.knowledge_graph.utils.s_expression_cache import (
    SExpressionCache,
)


# region GrailQAEntry definition
# region Function, Level definition
class Function(StrEnum):
    NONE = "none"
    COUNT = "count"
    ARGMIN = "argmin"
    ARGMAX = "argmax"
    LE = "le"
    LT = "lt"
    GE = "ge"
    GT = "gt"

    @staticmethod
    def from_str(function_str: str) -> "Function":
        match function_str.lower():
            case "none":
                return Function.NONE
            case "count":
                return Function.COUNT
            case "argmin":
                return Function.ARGMIN
            case "argmax":
                return Function.ARGMAX
            case "<=":
                return Function.LE
            case "<":
                return Function.LT
            case ">=":
                return Function.GE
            case ">":
                return Function.GT
            case _:
                raise ValueError(f"Unknown function: {function_str}")


class LEVEL(StrEnum):
    IID = "iid"
    COMPOSITIONAL = "compositional"
    ZERO_SHOT = "zero_shot"

    @staticmethod
    def from_str(level_str: str) -> "LEVEL":
        if level_str.lower() in ["iid", "i.i.d."]:
            return LEVEL.IID
        elif level_str.lower() in ["zero_shot", "zero-shot"]:
            return LEVEL.ZERO_SHOT
        elif level_str.lower() in ["compositional"]:
            return LEVEL.COMPOSITIONAL
        else:
            raise ValueError(f"Unknown level: {level_str}")


# endregion
# region Answer definition
class AnswerType(StrEnum):
    ENTITY = "entity"
    VALUE = "value"


class Answer(BaseModel):
    answer_type: AnswerType
    answer_argument: str
    entity_name: Optional[str] = None


# endregion
# region GraphQuery definition
class NodeType(StrEnum):
    CLASS = "class"
    ENTITY = "entity"
    LITERAL = "literal"


class Node(BaseModel):
    nid: int
    node_type: NodeType
    id_: str
    class_: str
    friendly_name: str
    question_node_flag: bool
    function: Function


class Edge(BaseModel):
    start: int
    end: int
    relation: str
    friendly_name: str


class GraphQuery(BaseModel):
    node_list: Sequence[Node]
    edge_list: Sequence[Edge]


# endregion
class GrailQAEntry(BaseModel):
    qid: int
    question: str
    answer_list: Sequence[Answer]
    function: Function
    num_node: int
    num_edge: int
    graph_query: GraphQuery
    sparql_query: str
    domain_list: Sequence[str]
    level: LEVEL
    s_expression: str


# endregion
# region ActionInfoEntry definition
class AgentActionInfo(BaseModel):
    action_name: str
    argument_list: Sequence[str]
    error_message_list: Optional[list[str]] = None


class SExpressionExecutionResult(BaseModel):
    # original -> simplified -> processed
    original: Sequence[str]
    simplified: Sequence[str]
    processed: Sequence[str]


class ActionInfo(BaseModel):
    agent_action_info_list: Sequence[AgentActionInfo]
    s_expression_execution_result: Optional[SExpressionExecutionResult]
    simplified_s_expression: str
    processed_s_expression: str
    entity_dict: Mapping[str, str]


class ActionInfoEntry(BaseModel):
    grail_qa_entry: GrailQAEntry
    action_info: Optional[ActionInfo]


# endregion
# region ActionListFactory definition
class PreparationResult(BaseModel):
    s_expression_entity_id_list: Sequence[str]
    simplified_s_expression: str


class AgentActionInfoListConstructionResult(BaseModel):
    agent_action_info_list: Sequence[AgentActionInfo]
    processed_s_expression: str


class ActionInfoFactory:
    def __init__(
        self,
        grail_qa_data_path_list: Sequence[str],
        sparql_executor: SparqlExecutor,
        ontology_dir_path: str,
        output_dir: str,
        log_file_path: str,
        s_expression_cache: SExpressionCache,
    ):
        # region Construct self.grail_qa_entry_list
        grail_qa_data_list: list[Mapping[str, Any]] = []
        for grail_data_path in grail_qa_data_path_list:
            grail_qa_data_list += json.load(open(grail_data_path))
        grail_qa_data_list = grail_qa_data_list
        grail_qa_entry_list: list[GrailQAEntry] = []
        for entry in tqdm(grail_qa_data_list, desc="Loading GrailQA data"):
            answer_list: list[Answer] = []
            for answer_entry in entry["answer"]:
                answer = Answer(
                    answer_type=AnswerType(answer_entry["answer_type"].lower()),
                    answer_argument=answer_entry["answer_argument"],
                    entity_name=answer_entry.get("entity_name"),
                )
                answer_list.append(answer)
            node_list: list[Node] = []
            for node_entry in entry["graph_query"]["nodes"]:
                question_node = node_entry["question_node"]
                assert question_node in [0, 1]
                node = Node(
                    nid=node_entry["nid"],
                    node_type=NodeType(node_entry["node_type"].lower()),
                    id_=node_entry["id"],
                    class_=node_entry["class"],
                    friendly_name=node_entry["friendly_name"],
                    question_node_flag=node_entry["question_node"] == 1,
                    function=Function.from_str(node_entry["function"]),
                )
                node_list.append(node)
            edge_list: list[Edge] = []
            for edge_entry in entry["graph_query"]["edges"]:
                edge = Edge(
                    start=edge_entry["start"],
                    end=edge_entry["end"],
                    relation=edge_entry["relation"],
                    friendly_name=edge_entry["friendly_name"],
                )
                edge_list.append(edge)
            graph_query = GraphQuery(node_list=node_list, edge_list=edge_list)
            level_str = entry.get("level", "i.i.d.")
            grail_qa_entry = GrailQAEntry(
                qid=entry["qid"],
                question=entry["question"],
                answer_list=answer_list,
                function=Function.from_str(entry["function"]),
                num_node=entry["num_node"],
                num_edge=entry["num_edge"],
                graph_query=graph_query,
                sparql_query=entry["sparql_query"],
                domain_list=entry["domains"],
                level=LEVEL.from_str(level_str),
                s_expression=entry["s_expression"],
            )
            grail_qa_entry_list.append(grail_qa_entry)
        self.grail_qa_entry_list: Sequence[GrailQAEntry] = grail_qa_entry_list
        # endregion
        self.sparql_executor = sparql_executor
        with open(os.path.join(ontology_dir_path, "vocab.json")) as f:
            vocab = json.load(f)
            self.attribute_list: Sequence[str] = vocab["attributes"]
            self.relation_list: Sequence[str] = vocab["relations"]
        range_info = {}
        with open(os.path.join(ontology_dir_path, "fb_roles"), "r") as f:
            for line in f:
                line = line.replace("\n", "")
                fields = line.split(" ")
                range_info[fields[1]] = fields[2]
        self.range_info: Mapping[str, str] = range_info
        reverse_property_dict = {}
        with open(os.path.join(ontology_dir_path, "reverse_properties")) as f:
            for line in f:
                line = line.replace("\n", "")
                fields = line.split("\t")
                reverse_property_dict[fields[0]] = fields[1]
        self.reverse_property_dict: Mapping[str, str] = reverse_property_dict
        self.action_info_entry_list_path = os.path.join(
            output_dir, "action_info_entry_list.json"
        )
        self.logger = SingletonLogger.get_instance(
            LoggerConfig(
                level="INFO",
                log_file_path=log_file_path,
                logger_name="knowledge_graph_standard_data_factory",
            )
        )
        self.s_expression_cache = s_expression_cache

    @staticmethod
    def _prepare(
        entry: GrailQAEntry,
    ) -> Optional[PreparationResult]:
        # region Validate the entry
        token_list: list[str] = entry.s_expression.split()
        strip_token_list: list[str] = []
        for token in token_list:
            while token[0] == "(":
                token = token[1:]
                token = token.strip()
            while token[-1] == ")":
                token = token[:-1]
                token = token.strip()
            strip_token_list.append(token)
        # region Validate the s_expression format
        match entry.function:
            case Function.NONE:
                assert (
                    len(
                        {
                            str(Function.COUNT).upper(),
                            str(Function.ARGMAX).upper(),
                            str(Function.ARGMIN).upper(),
                            str(Function.LE).lower(),
                            str(Function.LT).lower(),
                            str(Function.GE).lower(),
                            str(Function.GT).lower(),
                        }.intersection(set(strip_token_list))
                    )
                    == 0
                )
                first_node = entry.graph_query.node_list[0]
                assert first_node.node_type == NodeType.CLASS
                assert token_list[0] == "(AND"
                assert token_list[1] == first_node.id_
            case Function.COUNT | Function.ARGMAX | Function.ARGMIN:
                unselected_function_str_set: set[str] = {
                    str(Function.COUNT),
                    str(Function.ARGMAX),
                    str(Function.ARGMIN),
                }.difference({str(entry.function)})
                assert token_list[0] == f"({entry.function.upper()}"
                for unselected_function_str in unselected_function_str_set:
                    assert unselected_function_str.upper() not in strip_token_list
                assert (
                    len(
                        {
                            str(Function.LE),
                            str(Function.LT),
                            str(Function.GE),
                            str(Function.GT),
                        }.intersection(set(strip_token_list))
                    )
                    == 0
                )
            case Function.LE | Function.LT | Function.GE | Function.GT:
                return None
            case _:
                raise ValueError()
        # endregion
        # region Validate the entity
        node_entity_set: set[str] = set()
        s_expression_entity_id_list: list[str] = []
        for node in entry.graph_query.node_list:
            if node.node_type == NodeType.ENTITY:
                node_entity_set.add(node.id_)
        for strip_token in strip_token_list:
            if not KnowledgeGraphAPI._is_valid_entity(strip_token):  # noqa
                continue
            assert strip_token in node_entity_set
            assert strip_token not in s_expression_entity_id_list
            s_expression_entity_id_list.append(strip_token)
        if len(s_expression_entity_id_list) == 0:
            return None
        # endregion
        # region Validate node_list, s_expression structure
        node_type_id_set: set[str] = set()
        for node in entry.graph_query.node_list:
            if node.node_type == NodeType.CLASS and node.id_ in strip_token_list:
                node_type_id_set.add(node.id_)
        assert len(node_type_id_set) == 1
        answer_class = node_type_id_set.pop()
        # endregion
        # region Validate s_expression structure
        match entry.function:
            case Function.NONE:
                assert entry.s_expression.startswith(f"(AND {answer_class} (")
                assert entry.s_expression.endswith("))")
            case Function.COUNT | Function.ARGMAX | Function.ARGMIN:
                assert entry.s_expression.startswith(
                    f"({entry.function.upper()} (AND {answer_class} ("
                )
            case _:
                raise ValueError()
        # endregion
        # endregion
        # region Return PreparationResult
        assert entry.function in {
            Function.NONE,
            Function.COUNT,
            Function.ARGMAX,
            Function.ARGMIN,
        }
        # region Construct simplified_s_expression
        match entry.function:
            case Function.NONE:
                prefix = f"(AND {answer_class} "
                suffix = ")"
                simplified_s_expression = entry.s_expression[len(prefix) : -len(suffix)]
            case Function.COUNT | Function.ARGMAX | Function.ARGMIN:
                expression = SemanticParserUtil.lisp_to_nested_expression(
                    entry.s_expression
                )
                if entry.function == Function.COUNT:
                    assert len(expression) == 2
                else:
                    assert len(expression) == 3
                    if isinstance(expression[2], list):
                        return None
                expression[1] = expression[1][2]
                simplified_s_expression = SemanticParserUtil.expression_to_lisp(
                    expression
                )
            case _:
                raise ValueError()
        assert (
            LogicFormUtil.postprocess_raw_code(simplified_s_expression)
            == simplified_s_expression
        )
        # endregion
        # region Filter s_expression with literal
        literal_in_s_expression_flag = "^^" in entry.s_expression
        if literal_in_s_expression_flag:
            return None
        # endregion
        if not literal_in_s_expression_flag:
            assert answer_class is not None
            return PreparationResult(
                s_expression_entity_id_list=s_expression_entity_id_list,
                simplified_s_expression=simplified_s_expression,
            )
        # endregion

    def _construct_agent_action_info_list(
        self, entry: GrailQAEntry, preparation_result: PreparationResult
    ) -> AgentActionInfoListConstructionResult:
        def is_variable(_argument: str) -> bool:
            if not _argument.startswith("#"):
                return False
            return _argument[1:].isdigit()

        expression = SemanticParserUtil.lisp_to_nested_expression(
            preparation_result.simplified_s_expression
        )
        processed_expression = copy.deepcopy(expression)
        raw_sub_program_list: Sequence[Any] = LogicFormUtil.linearize_lisp_expression(
            expression, [0]
        )
        del expression
        agent_action_info_list: list[Any] = []
        variable_index_to_type_dict: dict[int, Optional[str]] = {}
        for sub_program_index, sub_program in enumerate(raw_sub_program_list):
            match sub_program[0]:
                case "JOIN":
                    assert len(sub_program) == 3
                    assert KnowledgeGraphAPI._is_valid_entity(  # noqa
                        sub_program[2]
                    ) or is_variable(sub_program[2])
                    error_message_list: list[str] = []
                    if isinstance(sub_program[1], str):
                        if sub_program[1] in self.reverse_property_dict:
                            relation = self.reverse_property_dict[sub_program[1]]

                            def reverse_in_relation(
                                _in_relation: str,
                                _out_relation: str,
                                _expression: list[Any],
                            ) -> list[Any]:
                                _expression = copy.deepcopy(_expression)
                                for (
                                    _inner_expression_index,
                                    _inner_expression,
                                ) in enumerate(_expression):
                                    assert isinstance(_inner_expression, (list, str))
                                    if isinstance(_inner_expression, list):
                                        if (
                                            len(_inner_expression) == 2
                                            and _inner_expression[0] == "R"
                                        ):
                                            continue
                                        _expression[_inner_expression_index] = (
                                            reverse_in_relation(
                                                _in_relation,
                                                _out_relation,
                                                _inner_expression,
                                            )
                                        )
                                    elif _inner_expression == _in_relation:
                                        _expression[_inner_expression_index] = [
                                            "R",
                                            _out_relation,
                                        ]
                                return _expression

                            processed_expression = reverse_in_relation(
                                sub_program[1], relation, processed_expression
                            )
                        else:
                            relation = sub_program[1]
                            error_message_list.append(
                                f"<REL>{relation}</REL> is an in_relation that cannot be reversed."
                            )
                    else:
                        assert (
                            isinstance(sub_program[1], list)
                            and len(sub_program[1]) == 2
                            and sub_program[1][0] == "R"
                        )
                        relation = sub_program[1][1]
                    if relation not in self.relation_list:
                        error_message_list.append(
                            f"<REL>{relation}</REL> is not in self.relation_list."
                        )
                    agent_action_info_list.extend(
                        [
                            AgentActionInfo(
                                action_name="get_relations",
                                argument_list=[sub_program[2]],
                            ),
                            AgentActionInfo(
                                action_name="get_neighbors",
                                argument_list=[sub_program[2], relation],
                                error_message_list=error_message_list or None,
                            ),
                        ]
                    )
                    generated_variable_index = sub_program_index
                    variable_index_to_type_dict[generated_variable_index] = (
                        self.range_info.get(relation)
                    )
                case "AND":
                    assert len(sub_program) == 3
                    assert is_variable(sub_program[1]) and is_variable(sub_program[2])
                    error_message_list = []
                    for argument in [sub_program[1], sub_program[2]]:
                        variable_index = int(argument[1:])
                        if variable_index_to_type_dict[variable_index] is None:
                            error_message_list.append(
                                f"<ARG>{argument}</ARG> do not have type information."
                            )
                    argument0_type = variable_index_to_type_dict[
                        int(sub_program[1][1:])
                    ]
                    argument1_type = variable_index_to_type_dict[
                        int(sub_program[2][1:])
                    ]
                    if (
                        len(error_message_list) == 0
                        and argument0_type != argument1_type
                    ):
                        error_message_list.append(
                            f"<ARG>{sub_program[1]}</ARG> and <ARG>{sub_program[2]}</ARG> have different types.\n"
                            f"<ARG>{sub_program[1]}</ARG> has type <TYPE>{argument0_type}</TYPE>.\n"
                            f"<ARG>{sub_program[2]}</ARG> has type <TYPE>{argument1_type}</TYPE>."
                        )
                    agent_action_info_list.append(
                        AgentActionInfo(
                            action_name="intersection",
                            argument_list=[sub_program[1], sub_program[2]],
                            error_message_list=error_message_list or None,
                        )
                    )
                    generated_variable_index = sub_program_index
                    if len(error_message_list) == 0:
                        variable_index_to_type_dict[generated_variable_index] = (
                            argument0_type
                        )
                    else:
                        variable_index_to_type_dict[generated_variable_index] = None
                case "COUNT":
                    assert sub_program_index == len(raw_sub_program_list) - 1
                    assert len(sub_program) == 2
                    assert is_variable(sub_program[1])
                    agent_action_info_list.append(
                        AgentActionInfo(
                            action_name="count",
                            argument_list=[sub_program[1]],
                        )
                    )
                case "ARGMAX" | "ARGMIN":
                    assert sub_program_index == len(raw_sub_program_list) - 1
                    assert len(sub_program) == 3
                    assert is_variable(sub_program[1])
                    assert isinstance(sub_program[2], str)
                    assert sub_program[2] in self.attribute_list
                    agent_action_info_list.extend(
                        [
                            AgentActionInfo(
                                action_name="get_attributes",
                                argument_list=[sub_program[1]],
                            ),
                            AgentActionInfo(
                                action_name=sub_program[0].lower(),
                                argument_list=[sub_program[1], sub_program[2]],
                            ),
                        ]
                    )
                case _:
                    raise ValueError()
        processed_s_expression = SemanticParserUtil.expression_to_lisp(
            processed_expression
        )
        assert (
            LogicFormUtil.postprocess_raw_code(processed_s_expression)
            == processed_s_expression
        )
        return AgentActionInfoListConstructionResult(
            agent_action_info_list=agent_action_info_list,
            processed_s_expression=processed_s_expression,
        )

    def construct(self) -> None:
        action_info_entry_list: list[ActionInfoEntry] = []
        for entry in tqdm(
            self.grail_qa_entry_list, desc="Constructing action_info_entry"
        ):
            preparation_result = self._prepare(entry)
            if preparation_result is None:
                action_info_entry_list.append(
                    ActionInfoEntry(
                        grail_qa_entry=entry,
                        action_info=None,
                    )
                )
                continue
            agent_action_info_list_construction_result = (
                self._construct_agent_action_info_list(entry, preparation_result)
            )
            entity_dict: dict[str, str] = {}
            for entity_id in preparation_result.s_expression_entity_id_list:
                for node in entry.graph_query.node_list:
                    if node.node_type == NodeType.ENTITY and node.id_ == entity_id:
                        entity_dict[node.friendly_name] = entity_id
            action_info_entry_list.append(
                ActionInfoEntry(
                    grail_qa_entry=entry,
                    action_info=ActionInfo(
                        agent_action_info_list=agent_action_info_list_construction_result.agent_action_info_list,
                        simplified_s_expression=preparation_result.simplified_s_expression,
                        processed_s_expression=agent_action_info_list_construction_result.processed_s_expression,
                        entity_dict=entity_dict,
                        s_expression_execution_result=None,
                    ),
                )
            )
        json.dump(
            [entry.model_dump() for entry in action_info_entry_list],
            open(self.action_info_entry_list_path, "w"),  # noqa
            indent=2,
        )

    def execute_s_expression(self) -> None:
        action_info_entry_list: list[ActionInfoEntry] = [
            ActionInfoEntry.model_validate(entry_dict)
            for entry_dict in json.load(open(self.action_info_entry_list_path))
        ]
        for entry in tqdm(action_info_entry_list, desc="Executing s_expression"):
            if entry.action_info is None:
                continue
            original_s_expression = entry.grail_qa_entry.s_expression
            simplified_s_expression = entry.action_info.simplified_s_expression
            processed_s_expression = entry.action_info.processed_s_expression
            for s_expression in [
                original_s_expression,
                simplified_s_expression,
                processed_s_expression,
            ]:
                if self.s_expression_cache.get_cache_item(s_expression) is not None:
                    continue
                else:
                    self.s_expression_cache.set_cache_item(
                        s_expression,
                        self.sparql_executor.execute_query(
                            LogicFormUtil.lisp_to_sparql(s_expression)
                        ),
                    )
            original_result = self.s_expression_cache.get_cache_item(
                original_s_expression
            )
            simplified_result = self.s_expression_cache.get_cache_item(
                simplified_s_expression
            )
            processed_result = self.s_expression_cache.get_cache_item(
                processed_s_expression
            )
            assert original_result is not None
            assert simplified_result is not None
            assert processed_result is not None
            entry.action_info.s_expression_execution_result = (
                SExpressionExecutionResult(
                    original=original_result,
                    simplified=simplified_result,
                    processed=processed_result,
                )
            )
        json.dump(
            [entry.model_dump() for entry in action_info_entry_list],
            open(self.action_info_entry_list_path, "w"),  # noqa
            indent=2,
        )

    def validate_action_info_entry(self) -> None:
        action_info_entry_list: list[ActionInfoEntry] = [
            ActionInfoEntry.model_validate(entry_dict)
            for entry_dict in json.load(open(self.action_info_entry_list_path))
        ]
        action_info_dict: dict[str, dict[str, list[int]]] = {
            "have_action_info": {},
            "not_have_action_info": {},
            "total": {},
        }
        error_message_info_dict: dict[
            str, dict[int, dict[str, dict[str, list[int]]]]
        ] = {}
        for action_info_entry in action_info_entry_list:
            function_str = str(action_info_entry.grail_qa_entry.function)
            qid = action_info_entry.grail_qa_entry.qid
            action_info_dict["total"].setdefault(function_str, []).append(qid)
            action_info_dict["total"].setdefault("total", []).append(qid)
            if action_info_entry.action_info is None:
                action_info_dict["not_have_action_info"].setdefault(
                    function_str, []
                ).append(qid)
                action_info_dict["not_have_action_info"].setdefault("total", []).append(
                    qid
                )
                continue
            else:
                action_info_dict["have_action_info"].setdefault("total", []).append(qid)
                action_info_dict["have_action_info"].setdefault(
                    function_str, []
                ).append(qid)
            s_expression_execution_result = (
                action_info_entry.action_info.s_expression_execution_result
            )
            assert s_expression_execution_result is not None
            assert len(s_expression_execution_result.processed) > 0
            assert set(s_expression_execution_result.simplified) == set(
                s_expression_execution_result.processed
            )
            action_info_list = action_info_entry.action_info.agent_action_info_list
            error_str_set: set[str] = set()
            for action_info in action_info_list:
                error_message_list = action_info.error_message_list
                if error_message_list is None:
                    continue
                for error_message in error_message_list:
                    if "cannot be reversed" in error_message:
                        error_str_set.add("contain_irreversible_in_relation")
                    elif "not in self.relation_list" in error_message:
                        if len(error_message_list) == 2:
                            error_str_set.add("contain_out_of_range_in_relation")
                        else:
                            error_str_set.add("contain_out_of_range_out_relation")
                    elif "do not have type information" in error_message:
                        error_str_set.add("contain_unknown_relation_type")
                    elif "have different types" in error_message:
                        error_str_set.add("intersection_relation_type_mismatch")
            trajectory_length = len(action_info_list)
            error_str_key_list = ["total"]
            if len(error_str_set) == 0:
                error_str_key_list.append("no_error")
            else:
                error_str_key_list.append("have_error")
                if len(error_str_set) == 1:
                    error_str_key_list.append(f"only__{error_str_set.pop()}")
                else:
                    for error_str in error_str_set:
                        error_str_key_list.append(f"contain__{error_str}")
            for function_key in ["total", function_str]:
                if function_key not in error_message_info_dict:
                    error_message_info_dict[function_key] = {}
                if trajectory_length not in error_message_info_dict[function_key]:
                    error_message_info_dict[function_key][trajectory_length] = {}
                for error_str in error_str_key_list:
                    if (
                        error_str
                        not in error_message_info_dict[function_key][trajectory_length]
                    ):
                        error_message_info_dict[function_key][trajectory_length][
                            error_str
                        ] = {
                            "no_empty_processed_s_expression": [],
                            "empty_processed_s_expression": [],
                            "total": [],
                        }
                    if len(s_expression_execution_result.processed) == 0:
                        error_message_info_dict[function_key][trajectory_length][
                            error_str
                        ]["empty_processed_s_expression"].append(qid)
                    else:
                        error_message_info_dict[function_key][trajectory_length][
                            error_str
                        ]["no_empty_processed_s_expression"].append(qid)
                    error_message_info_dict[function_key][trajectory_length][error_str][
                        "total"
                    ].append(qid)

        def dfs_print(d: dict[str, Any], accumulated_key: str) -> None:
            sorted_key_list = sorted(d.keys())
            for key in sorted_key_list:
                value = d[key]
                if isinstance(value, dict):
                    dfs_print(value, f"{accumulated_key}-{key}")
                else:
                    assert isinstance(value, list)
                    print(f"{accumulated_key}-{key}: {len(value)}")

        dfs_print(action_info_dict, "")
        print("=" * 20)
        dfs_print(error_message_info_dict, "")


# endregion
def main() -> None:
    sparql_executor = SparqlExecutor("http://222.201.139.67:3001/sparql")
    action_info_factory = ActionInfoFactory(
        grail_qa_data_path_list=[
            "data/v0303/knowledge_graph/raw/download/grail_qa/grailqa_v1.0_train.json",
            "data/v0303/knowledge_graph/raw/download/grail_qa/grailqa_v1.0_dev.json",
        ],
        sparql_executor=sparql_executor,
        ontology_dir_path="data/v0121/knowledge_graph/ontology",
        output_dir="data/v0303/knowledge_graph/raw/action_info_factory/v0415",
        log_file_path="./outputs/data/v0303/os_interaction/action_info_factory.log",
        s_expression_cache=SExpressionCache(
            cache_path="data/v0303/knowledge_graph/cache/s_expression_cache_dict.json"
        ),
    )
    # action_info_factory.construct()
    action_info_factory.execute_s_expression()
    # action_info_factory.validate_action_info_entry()


if __name__ == "__main__":
    main()
