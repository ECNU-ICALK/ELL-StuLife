from typing import Tuple, Iterator
import sqlglot
from sqlglot import expressions
from pydantic import BaseModel

from src.tasks.instance.db_bench.task import DBBenchSkillUtility


class SkillEvaluator:
    @staticmethod
    def _is_calculation_in_having(node: expressions.Expression) -> bool:
        complex_operators = {
            expressions.Add,
            expressions.Sub,
            expressions.Mul,
            expressions.Div,
            expressions.Mod,
        }
        for sub_node in node.walk():
            if isinstance(sub_node, tuple(complex_operators)):
                return True
        return False

    @staticmethod
    def evaluate(ast: expressions.Expression) -> set[str]:
        skill_set: set[str] = set()  # Set of skills to be returned
        # region Check for select, insert, delete, update
        if ast.find(expressions.Select):
            skill_set.add("select")
        if ast.find(expressions.Insert):
            skill_set.add("insert")
        if ast.find(expressions.Delete):
            skill_set.add("delete")
        if ast.find(expressions.Update):
            skill_set.add("update")
        # endregion
        # region Check for WHERE
        # Check for where_single_condition, where_multiple_conditions, where_nested_conditions
        if where_expr := ast.find(expressions.Where):
            if condition := where_expr.args.get("this"):
                # Check for where_multiple_conditions and where_nested_conditions
                if isinstance(condition, (expressions.And, expressions.Or)):
                    has_nested = any(
                        isinstance(sub_node, (expressions.And, expressions.Or))
                        for sub_node in condition.walk()
                        if sub_node is not condition
                    )
                    if has_nested:
                        skill_set.add("where_nested_conditions")
                    else:
                        skill_set.add("where_multiple_conditions")
                else:
                    skill_set.add("where_single_condition")
        # endregion
        # region Check for GROUP BY.
        # Check for group_by_single_column, group_by_multiple_columns
        if group_by_expr := ast.args.get("group"):
            if len(group_by_expr.expressions) == 1:
                skill_set.add("group_by_single_column")
            else:
                skill_set.add("group_by_multiple_columns")
        # endregion
        # region Check for HAVING
        # Check for having_single_condition_with_aggregate, having_multiple_conditions_with_aggregate,
        #   having_aggregate_calculation
        if having_expr := ast.args.get("having"):
            if condition := having_expr.args.get("this"):
                if isinstance(condition, (expressions.And, expressions.Or)):
                    skill_set.add("having_multiple_conditions_with_aggregate")
                    if SkillEvaluator._is_calculation_in_having(condition):
                        skill_set.add("having_aggregate_calculation")
                else:
                    has_aggregate = any(
                        isinstance(node, expressions.Func)
                        for node in condition.walk()
                        if isinstance(node, expressions.Func)
                    )
                    if has_aggregate:
                        skill_set.add("having_single_condition_with_aggregate")
                        if SkillEvaluator._is_calculation_in_having(condition):
                            skill_set.add("having_aggregate_calculation")
        # endregion
        # region Check for ORDER BY
        # Check for order_by_single_column, order_by_multiple_columns_same_direction,
        #   order_by_multiple_columns_different_directions
        if order_by_expr := ast.args.get("order"):
            order_by_columns = order_by_expr.expressions
            directions = []
            for expr in order_by_columns:
                # Determine sort direction: 'DESC' if descending, else 'ASC'
                desc = expr.args.get("desc")
                direction = "DESC" if desc else "ASC"
                directions.append(direction)
            if len(order_by_columns) == 1:
                skill_set.add("order_by_single_column")
            else:
                if len(set(directions)) == 1:
                    skill_set.add("order_by_multiple_columns_same_direction")
                else:
                    skill_set.add("order_by_multiple_columns_different_directions")
        # endregion
        # region Check for LIMIT and OFFSET
        # Check for limit_only, limit_and_offset
        if ast.args.get("limit"):
            if ast.args.get("offset"):
                skill_set.add("limit_and_offset")
            else:
                skill_set.add("limit_only")
        # endregion
        # region Check for Alias
        # Check for column_alias, table_alias
        if select_expr := ast.find(expressions.Select):
            for expr in select_expr.expressions:
                if isinstance(expr, expressions.Alias):
                    skill_set.add("column_alias")
        if from_expr := ast.find(expressions.From):
            if from_expr.args["this"].alias != "":
                skill_set.add("table_alias")
        # endregion
        # region Check for subqueries
        # Check for subquery_single, subquery_multiple, subquery_nested
        main_level_subqueries = []
        subquery_nodes = list(ast.find_all(expressions.Subquery))
        for subquery in subquery_nodes:
            is_nested = False
            parent = subquery.parent
            while parent:
                if parent in subquery_nodes:
                    is_nested = True
                    break
                parent = parent.parent
            del parent
            if is_nested:
                skill_set.add("subquery_nested")
            else:
                main_level_subqueries.append(subquery)
        if len(main_level_subqueries) > 1:
            skill_set.add("subquery_multiple")
        elif len(main_level_subqueries) == 1 and "subquery_nested" not in skill_set:
            skill_set.add("subquery_single")
        # endregion
        return skill_set
