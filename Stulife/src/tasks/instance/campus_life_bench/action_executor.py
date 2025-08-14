"""
Action Executor for CampusLifeBench
Handles parsing and execution of Action: formatted commands
All natural language communications/returns MUST use English only
"""

import re
import ast
from typing import Dict, Any, Optional, List, Tuple
import sys
import os

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from tools import ToolResult, ensure_english_message
    from environment import CampusEnvironment
except ImportError:
    try:
        from .tools import ToolResult, ensure_english_message
        from .environment import CampusEnvironment
    except ImportError:
        # Absolute import fallback
        from tasks.instance.campus_life_bench.tools import ToolResult, ensure_english_message
        from tasks.instance.campus_life_bench.environment import CampusEnvironment


class ActionExecutor:
    """
    Executes Action: formatted commands by mapping them to environment methods
    """
    
    def __init__(self, environment: CampusEnvironment, available_systems: Optional[List[str]] = None):
        """
        Initialize action executor
        
        Args:
            environment: Campus environment instance
            available_systems: List of available system names (None = all systems available)
        """
        self.environment = environment
        self.available_systems = available_systems or self._get_all_systems()
        self.action_mapping = self._build_action_mapping()
    
    def _get_all_systems(self) -> List[str]:
        """Get list of all available systems"""
        return [
            "email", "calendar", "map", "geography", "reservation", 
            "bibliography", "data_system", "course_selection", "draft", "registration"
        ]
    
    def _build_action_mapping(self) -> Dict[str, str]:
        """
        Build mapping from action names to environment method names
        
        Returns:
            Dictionary mapping action names to method names
        """
        mapping = {}
        
        # Email system mappings
        if "email" in self.available_systems:
            mapping.update({
                "email.send_email": "send_email",
                "email.view_inbox": "view_inbox", 
                "email.reply_email": "reply_email",
                "email.delete_email": "delete_email"
            })
        
        # Calendar system mappings
        if "calendar" in self.available_systems:
            mapping.update({
                "calendar.add_event": "add_event",
                "calendar.remove_event": "remove_event",
                "calendar.update_event": "update_event",
                "calendar.view_schedule": "view_schedule",
                "calendar.query_advisor_availability": "query_advisor_availability"
            })
        
        # Map system mappings
        if "map" in self.available_systems:
            mapping.update({
                "map.find_building_id": "find_building_id",
                "map.get_building_details": "get_building_details",
                "map.find_room_location": "find_room_location",
                "map.find_optimal_path": "find_optimal_path",
                "map.query_buildings_by_property": "query_buildings_by_property",
                "map.get_building_complex_info": "get_building_complex_info",
                "map.list_valid_query_properties": "list_valid_query_properties"
            })
        
        # Geography system mappings
        if "geography" in self.available_systems:
            mapping.update({
                "geography.get_current_location": "get_current_location",
                "geography.set_location": "set_location",
                "geography.walk_to": "walk_to"
            })
        
        # Reservation system mappings
        if "reservation" in self.available_systems:
            mapping.update({
                "reservation.query_availability": "query_availability",
                "reservation.make_booking": "make_booking"
            })
        
        # Information system mappings
        if "bibliography" in self.available_systems:
            mapping.update({
                "bibliography.list_chapters": "list_chapters",
                "bibliography.list_sections": "list_sections",
                "bibliography.list_articles": "list_articles",
                "bibliography.view_article": "view_article"
            })
        
        if "data_system" in self.available_systems:
            mapping.update({
                "data_system.list_by_category": "list_by_category",
                "data_system.query_by_identifier": "query_by_identifier",
                "data_system.list_books_by_category": "list_books_by_category",
                "data_system.search_books": "search_books"
            })
        
        # Course selection system mappings
        if "course_selection" in self.available_systems:
            mapping.update({
                "course_selection.browse_courses": "browse_courses"
            })
        
        if "draft" in self.available_systems:
            mapping.update({
                "draft.add_course": "add_course",
                "draft.remove_course": "remove_course",
                "draft.assign_pass": "assign_pass",
                "draft.view": "view_draft"
            })
        
        if "registration" in self.available_systems:
            mapping.update({
                "registration.submit_draft": "submit_draft"
            })
        
        return mapping
    
    def execute_action(self, action_content: str) -> ToolResult:
        """
        Execute an action command
        
        Args:
            action_content: Action content in format "tool_name(params...)"
            
        Returns:
            ToolResult from the executed action
        """
        try:
            # Parse the action
            action_name, params = self._parse_action_content(action_content)
            
            # Check if action is available
            if action_name not in self.action_mapping:
                available_actions = list(self.action_mapping.keys())
                return ToolResult.failure(
                    ensure_english_message(
                        f"Action '{action_name}' is not available. Available actions: {', '.join(available_actions)}"
                    )
                )

            # Additional validation: check if the system is actually available
            system_name = action_name.split('.')[0] if '.' in action_name else action_name
            if system_name not in self.available_systems:
                return ToolResult.failure(
                    ensure_english_message(
                        f"System '{system_name}' is not available for this task. Available systems: {', '.join(self.available_systems)}"
                    )
                )
            
            # Get the corresponding environment method
            method_name = self.action_mapping[action_name]
            method = getattr(self.environment, method_name)

            # Apply parameter mapping for specific methods
            mapped_params = self._map_parameters(action_name, params)

            # Execute the method with mapped parameters
            result = method(**mapped_params)
            
            # Ensure result is a ToolResult
            if not isinstance(result, ToolResult):
                return ToolResult.error(
                    ensure_english_message(f"Method {method_name} did not return a ToolResult")
                )
            
            return result
            
        except Exception as e:
            return ToolResult.error(
                ensure_english_message(f"Failed to execute action '{action_content}': {str(e)}")
            )
    
    def _parse_action_content(self, action_content: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse action content to extract action name and parameters
        
        Args:
            action_content: Content like "email.send_email(to=\"test@test.com\", subject=\"Test\")"
            
        Returns:
            Tuple of (action_name, parameters_dict)
        """
        # Extract action name and parameters
        match = re.match(r'([^(]+)\((.*)\)', action_content.strip())
        if not match:
            raise ValueError(f"Invalid action format: {action_content}")
        
        action_name = match.group(1).strip()
        params_str = match.group(2).strip()
        
        # Parse parameters
        params = {}
        if params_str:
            params = self._parse_parameters(params_str)
        
        return action_name, params
    
    def _parse_parameters(self, params_str: str) -> Dict[str, Any]:
        """
        Parse parameter string into dictionary
        
        Args:
            params_str: Parameter string like 'to="test@test.com", subject="Test"'
            
        Returns:
            Dictionary of parsed parameters
        """
        params = {}
        
        # Handle empty parameters
        if not params_str.strip():
            return params
        
        try:
            # Try to parse as Python function call arguments
            # Create a dummy function call and parse it
            dummy_call = f"dummy_func({params_str})"
            parsed = ast.parse(dummy_call, mode='eval')
            
            # Extract arguments from the parsed AST
            call_node = parsed.body
            
            # Handle keyword arguments
            for keyword in call_node.keywords:
                param_name = keyword.arg
                param_value = self._extract_ast_value(keyword.value)
                params[param_name] = param_value
            
            # Handle positional arguments (convert to keyword based on common patterns)
            for i, arg in enumerate(call_node.args):
                # This is a simplified approach - in practice, you'd need method signatures
                param_value = self._extract_ast_value(arg)
                params[f"arg_{i}"] = param_value
                
        except Exception as e:
            # Fallback: simple regex parsing for basic cases
            params = self._parse_parameters_fallback(params_str)
        
        return params
    
    def _extract_ast_value(self, node) -> Any:
        """Extract value from AST node"""
        try:
            if isinstance(node, ast.Constant):
                return node.value
            elif hasattr(ast, 'Str') and isinstance(node, ast.Str):  # Python < 3.8 compatibility
                return node.s
            elif hasattr(ast, 'Num') and isinstance(node, ast.Num):  # Python < 3.8 compatibility
                return node.n
            elif hasattr(ast, 'NameConstant') and isinstance(node, ast.NameConstant):  # Python < 3.8 compatibility
                return node.value
            elif isinstance(node, ast.Dict):
                # Handle dictionary literals
                result = {}
                for key, value in zip(node.keys, node.values):
                    key_val = self._extract_ast_value(key)
                    val_val = self._extract_ast_value(value)
                    result[key_val] = val_val
                return result
            elif isinstance(node, ast.List):
                # Handle list literals
                return [self._extract_ast_value(item) for item in node.elts]
            elif isinstance(node, ast.Name):
                # Handle variable names (convert to string)
                return node.id
            else:
                # For complex expressions, convert back to string
                if hasattr(ast, 'unparse'):
                    return ast.unparse(node)
                else:
                    # Fallback for older Python versions
                    return repr(node)
        except Exception:
            # Fallback: return string representation
            return str(node)
    
    def _parse_parameters_fallback(self, params_str: str) -> Dict[str, Any]:
        """
        Fallback parameter parsing using regex

        Args:
            params_str: Parameter string

        Returns:
            Dictionary of parsed parameters
        """
        params = {}

        # Enhanced regex patterns for different value types
        patterns = [
            # String values: key="value" or key='value'
            (r'(\w+)\s*=\s*["\']([^"\']*)["\']', str),
            # Boolean values: key=True or key=False
            (r'(\w+)\s*=\s*(True|False)', lambda x: x == 'True'),
            # Numeric values: key=123 or key=123.45
            (r'(\w+)\s*=\s*(\d+\.?\d*)', lambda x: float(x) if '.' in x else int(x)),
            # Dictionary values: key={"a": "b"} (simplified)
            (r'(\w+)\s*=\s*(\{[^}]*\})', lambda x: eval(x) if x.startswith('{') else x),
        ]

        for pattern, converter in patterns:
            matches = re.findall(pattern, params_str)
            for key, value in matches:
                if key not in params:  # Don't override already parsed values
                    try:
                        params[key] = converter(value) if callable(converter) else converter
                    except Exception:
                        params[key] = value  # Fallback to string

        return params
    
    def get_available_actions(self) -> List[str]:
        """
        Get list of available action names
        
        Returns:
            List of available action names
        """
        return list(self.action_mapping.keys())
    
    def is_action_available(self, action_name: str) -> bool:
        """
        Check if an action is available
        
        Args:
            action_name: Name of the action to check
            
        Returns:
            True if action is available, False otherwise
        """
        return action_name in self.action_mapping

    def _map_parameters(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map action parameters to environment method parameters

        Args:
            action_name: Name of the action
            params: Original parameters

        Returns:
            Mapped parameters
        """
        # Parameter mapping for specific actions
        parameter_mappings = {
            "email.send_email": {
                "to": "recipient",  # Map 'to' parameter to 'recipient'
                "subject": "subject",
                "body": "body",
                "cc": "cc"
            },
            "email.reply_email": {
                "email_id": "email_id",
                "body": "body"
            },
            "email.delete_email": {
                "email_id": "email_id"
            },
            "email.view_inbox": {
                "filter_unread": "filter_unread"
            }
        }

        if action_name in parameter_mappings:
            mapping = parameter_mappings[action_name]
            mapped_params = {}

            for original_param, value in params.items():
                if original_param in mapping:
                    mapped_param = mapping[original_param]
                    mapped_params[mapped_param] = value
                else:
                    # Keep unmapped parameters as-is
                    mapped_params[original_param] = value

            return mapped_params
        else:
            # No mapping needed, return original parameters
            return params
