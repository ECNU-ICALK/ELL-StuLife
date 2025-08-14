"""
Test suite for the new Action-based system in CampusLifeBench
All natural language communications/returns MUST use English only
"""

import unittest
import json
from unittest.mock import Mock, patch
from src.tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem, AgentAction
from src.tasks.instance.campus_life_bench.action_executor import ActionExecutor
from src.tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator
from src.tasks.instance.campus_life_bench.environment import CampusEnvironment
from src.tasks.instance.campus_life_bench.tools import ToolResult


class TestActionSystem(unittest.TestCase):
    """Test the new Action-based execution system"""
    
    def setUp(self):
        """Set up test environment"""
        self.campus_environment = CampusEnvironment()
        self.prompt_generator = SystemPromptGenerator()
    
    def test_action_parsing_valid_format(self):
        """Test parsing of valid Action: format"""
        test_cases = [
            'Action: email.send_email(to="test@test.com", subject="Test", body="Hello")',
            'Action: geography.get_current_location()',
            'Action: finish()',
            'Action: map.find_building_id(building_name="Library")'
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                result = CampusTask._parse_agent_response(test_case)
                self.assertIn(result.action, [AgentAction.EXECUTE, AgentAction.FINISH])
    
    def test_action_parsing_invalid_format(self):
        """Test parsing of invalid formats"""
        test_cases = [
            "Just some text without action",
            "Action: invalid_format",
            "```python\ncode_block()\n```",  # Old format should be invalid now
            "Action: (missing_action_name)"
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                result = CampusTask._parse_agent_response(test_case)
                self.assertEqual(result.action, AgentAction.INVALID)
    
    def test_action_executor_system_filtering(self):
        """Test that ActionExecutor only allows actions from available systems"""
        # Test with limited systems
        limited_systems = ["email", "calendar"]
        executor = ActionExecutor(self.campus_environment, limited_systems)
        
        # Should allow email actions
        result = executor.execute_action('email.send_email(to="test@test.com", subject="Test", body="Hello")')
        self.assertIsInstance(result, ToolResult)
        
        # Should reject map actions
        result = executor.execute_action('map.find_building_id(building_name="Library")')
        self.assertTrue(result.is_failure())
        self.assertIn("not available", result.message)
    
    def test_system_prompt_generation(self):
        """Test dynamic system prompt generation"""
        # Test with all systems
        prompt_all = self.prompt_generator.generate_prompt()
        self.assertIn("Email System Tools", prompt_all)
        self.assertIn("Map & Geography Tools", prompt_all)
        self.assertIn("Course Selection System Tools", prompt_all)
        
        # Test with limited systems
        limited_systems = ["email", "calendar"]
        prompt_limited = self.prompt_generator.generate_prompt(limited_systems)
        self.assertIn("Email System Tools", prompt_limited)
        self.assertIn("Calendar System Tools", prompt_limited)
        self.assertNotIn("Map & Geography Tools", prompt_limited)
    
    def test_dataset_item_available_systems(self):
        """Test CampusDatasetItem with available_systems field"""
        # Test with specific systems
        item_data = {
            "task_id": "test_001",
            "task_type": "email_sending",
            "instruction": "Send an email",
            "available_systems": ["email"]
        }
        
        item = CampusDatasetItem(**item_data)
        self.assertEqual(item.available_systems, ["email"])
        self.assertEqual(item.get_available_systems(), ["email"])
        
        # Test with no systems specified (should be None)
        item_data_no_systems = {
            "task_id": "test_002",
            "task_type": "multi_system",
            "instruction": "Complete multiple tasks"
        }
        
        item_no_systems = CampusDatasetItem(**item_data_no_systems)
        self.assertIsNone(item_no_systems.available_systems)
    
    def test_task_system_availability_logic(self):
        """Test CampusTask system availability logic"""
        task = CampusTask()
        
        # Test with explicit available_systems
        item_with_systems = CampusDatasetItem(
            task_id="test_001",
            task_type="email_sending",
            instruction="Send email",
            available_systems=["email"]
        )
        
        available = task._get_available_systems(item_with_systems)
        self.assertEqual(available, ["email"])
        
        # Test with task_type defaults
        item_email_type = CampusDatasetItem(
            task_id="test_002",
            task_type="email_sending",
            instruction="Send email"
        )
        
        available_default = task._get_available_systems(item_email_type)
        self.assertEqual(available_default, ["email"])
        
        # Test with multi_system type (should return None for all systems)
        item_multi = CampusDatasetItem(
            task_id="test_003",
            task_type="multi_system",
            instruction="Multiple tasks"
        )
        
        available_multi = task._get_available_systems(item_multi)
        self.assertIsNone(available_multi)
    
    def test_action_parameter_parsing(self):
        """Test parameter parsing in ActionExecutor"""
        executor = ActionExecutor(self.campus_environment, ["email"])
        
        # Test simple string parameters
        action_name, params = executor._parse_action_content(
            'email.send_email(to="test@test.com", subject="Test Subject")'
        )
        
        self.assertEqual(action_name, "email.send_email")
        self.assertIn("to", params)
        self.assertIn("subject", params)
        self.assertEqual(params["to"], "test@test.com")
        self.assertEqual(params["subject"], "Test Subject")
    
    def test_action_validation(self):
        """Test action validation logic"""
        executor = ActionExecutor(self.campus_environment, ["email", "calendar"])
        
        # Test valid actions
        self.assertTrue(executor.is_action_available("email.send_email"))
        self.assertTrue(executor.is_action_available("calendar.add_event"))
        
        # Test invalid actions
        self.assertFalse(executor.is_action_available("map.find_building_id"))
        self.assertFalse(executor.is_action_available("nonexistent.action"))
        
        # Test available actions list
        available_actions = executor.get_available_actions()
        self.assertIn("email.send_email", available_actions)
        self.assertIn("calendar.add_event", available_actions)
        self.assertNotIn("map.find_building_id", available_actions)
    
    def test_english_only_enforcement(self):
        """Test that all messages are in English only"""
        executor = ActionExecutor(self.campus_environment, ["email"])
        
        # Execute a valid action
        result = executor.execute_action('email.send_email(to="test@test.com", subject="Test", body="Hello")')
        
        # Check that the message is in English
        self.assertIsInstance(result.message, str)
        # Simple check for English characters only
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-:()[]{}\"'")
        self.assertTrue(all(char in allowed_chars for char in result.message))
    
    def test_backward_compatibility(self):
        """Test backward compatibility with finish() format"""
        # Test old finish() format
        result = CampusTask._parse_agent_response("finish()")
        self.assertEqual(result.action, AgentAction.FINISH)
        
        # Test new Action: finish() format
        result_new = CampusTask._parse_agent_response("Action: finish()")
        self.assertEqual(result_new.action, AgentAction.FINISH)


class TestSystemIntegration(unittest.TestCase):
    """Test integration between different components"""
    
    def setUp(self):
        """Set up test environment"""
        self.task = CampusTask()
    
    @patch('src.tasks.instance.campus_life_bench.task.CampusTask._get_current_dataset_item')
    def test_full_action_execution_flow(self, mock_get_item):
        """Test the complete flow from task setup to action execution"""
        # Mock dataset item with limited systems
        mock_item = CampusDatasetItem(
            task_id="integration_test",
            task_type="email_sending",
            instruction="Send an email",
            available_systems=["email"]
        )
        mock_get_item.return_value = mock_item
        
        # Create mock session
        mock_session = Mock()
        mock_session.chat_history = Mock()
        mock_session.chat_history.add_item = Mock()
        
        # Test _reset method (should initialize action executor and add system prompt)
        self.task._reset(mock_session)
        
        # Verify action executor was initialized
        self.assertIsNotNone(self.task.action_executor)
        self.assertEqual(self.task.action_executor.available_systems, ["email"])
        
        # Verify system prompt was added
        mock_session.chat_history.add_item.assert_called()
        call_args = mock_session.chat_history.add_item.call_args[0][0]
        self.assertIn("Email System Tools", call_args.content)
        self.assertNotIn("Map & Geography Tools", call_args.content)


if __name__ == '__main__':
    unittest.main()
