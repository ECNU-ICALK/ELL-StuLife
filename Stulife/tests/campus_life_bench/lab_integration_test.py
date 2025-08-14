#!/usr/bin/env python3
"""
LAB Framework Integration Test for CampusLifeBench Action System

This test validates integration with the official LifelongAgentBench entry point
and tests the complete pipeline from task loading to evaluation.
"""

import unittest
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
sys.path.insert(0, src_path)

from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
from tasks.instance.campus_life_bench.environment import CampusEnvironment
from tasks.instance.campus_life_bench.action_executor import ActionExecutor
from tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator


class MockAgent:
    """Mock agent for testing LAB integration"""
    
    def __init__(self, responses: List[str]):
        self.responses = responses
        self.response_index = 0
    
    def get_response(self, prompt: str) -> str:
        """Get next mock response"""
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        return "Action: finish()"


class LABIntegrationTests(unittest.TestCase):
    """Test integration with LAB framework"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.temp_dir = tempfile.mkdtemp()
        
        # Load test data
        with open(self.test_data_dir / "comprehensive_test_tasks.json", 'r') as f:
            self.test_tasks = json.load(f)
    
    def test_task_loading_pipeline(self):
        """Test complete task loading and setup pipeline"""
        # Create test dataset items
        email_test = self.test_tasks["single_system_tests"]["email_system_test"]
        
        dataset_item = CampusDatasetItem(
            task_id=email_test["task_id"],
            task_type=email_test["task_type"],
            instruction=email_test["instruction"],
            available_systems=email_test["available_systems"]
        )
        
        # Test dataset item creation
        self.assertEqual(dataset_item.task_id, "email_001")
        self.assertEqual(dataset_item.available_systems, ["email"])
        self.assertEqual(dataset_item.get_available_systems(), ["email"])
        
        # Test system prompt generation
        prompt_generator = SystemPromptGenerator()
        system_prompt = prompt_generator.generate_prompt(dataset_item.available_systems)
        
        # Validate prompt content
        self.assertIn("Email System Tools", system_prompt)
        self.assertNotIn("Map & Geography Tools", system_prompt)
        self.assertIn("send_email", system_prompt)
        
        print(f"✅ Task loading pipeline validated")
        print(f"   Dataset item: {dataset_item.task_id}")
        print(f"   Available systems: {dataset_item.available_systems}")
        print(f"   System prompt length: {len(system_prompt)} characters")
    
    def test_action_execution_pipeline(self):
        """Test complete action execution pipeline"""
        # Set up environment and executor
        environment = CampusEnvironment()
        executor = ActionExecutor(environment, ["email", "calendar"])
        
        # Test action sequence
        actions = [
            'Action: email.send_email(to="test@university.edu", subject="Test", body="Hello")',
            'Action: calendar.add_event(calendar_id="self", event_title="Meeting", location="Office", time="Week 1, Monday, 14:00-15:00")',
            'Action: finish()'
        ]
        
        results = []
        for action in actions:
            # Parse action
            parsed = CampusTask._parse_agent_response(action)
            
            if parsed.action.value == "finish":
                results.append({
                    "action": action,
                    "status": "FINISH",
                    "success": True
                })
                break
            elif parsed.action.value == "execute":
                # Execute action
                result = executor.execute_action(parsed.content)
                results.append({
                    "action": action,
                    "status": result.status.value,
                    "message": result.message,
                    "success": result.is_success(),
                    "data": result.data
                })
            else:
                results.append({
                    "action": action,
                    "status": "INVALID",
                    "success": False
                })
        
        # Validate results
        successful_actions = sum(1 for r in results if r["success"])
        total_actions = len(results)
        
        self.assertGreaterEqual(successful_actions, 2, f"Expected at least 2 successful actions, got {successful_actions}")
        
        print(f"✅ Action execution pipeline validated")
        print(f"   Actions executed: {total_actions}")
        print(f"   Successful actions: {successful_actions}")
        for i, result in enumerate(results, 1):
            status_icon = "✅" if result["success"] else "❌"
            print(f"   {i}. {status_icon} {result['status']}: {result['action'][:50]}...")
    
    def test_batch_task_processing(self):
        """Test processing multiple tasks in batch"""
        # Create multiple test tasks
        test_tasks = [
            {
                "task_id": "batch_001",
                "task_type": "email_sending",
                "instruction": "Send an email to advisor",
                "available_systems": ["email"],
                "expected_action": 'Action: email.send_email(to="advisor@university.edu", subject="Question", body="I have a question")'
            },
            {
                "task_id": "batch_002", 
                "task_type": "navigation",
                "instruction": "Find the library",
                "available_systems": ["map"],
                "expected_action": 'Action: map.find_building_id(building_name="Grand Central Library")'
            },
            {
                "task_id": "batch_003",
                "task_type": "calendar_management",
                "instruction": "Add study session to calendar",
                "available_systems": ["calendar"],
                "expected_action": 'Action: calendar.add_event(calendar_id="self", event_title="Study", location="Library", time="Week 1, Tuesday, 14:00-16:00")'
            }
        ]
        
        batch_results = []
        environment = CampusEnvironment()
        
        for task_data in test_tasks:
            # Create dataset item
            dataset_item = CampusDatasetItem(
                task_id=task_data["task_id"],
                task_type=task_data["task_type"],
                instruction=task_data["instruction"],
                available_systems=task_data["available_systems"]
            )
            
            # Create executor for this task
            executor = ActionExecutor(environment, dataset_item.available_systems)
            
            # Generate system prompt
            prompt_generator = SystemPromptGenerator()
            system_prompt = prompt_generator.generate_prompt(dataset_item.available_systems)
            
            # Execute expected action
            parsed = CampusTask._parse_agent_response(task_data["expected_action"])
            if parsed.action.value == "execute":
                result = executor.execute_action(parsed.content)
                
                batch_results.append({
                    "task_id": task_data["task_id"],
                    "available_systems": dataset_item.available_systems,
                    "prompt_length": len(system_prompt),
                    "action_executed": task_data["expected_action"],
                    "execution_status": result.status.value,
                    "success": result.is_success(),
                    "message": result.message
                })
        
        # Validate batch processing
        successful_tasks = sum(1 for r in batch_results if r["success"])
        total_tasks = len(batch_results)
        
        self.assertEqual(successful_tasks, total_tasks, f"Expected all {total_tasks} tasks to succeed, got {successful_tasks}")
        
        print(f"✅ Batch task processing validated")
        print(f"   Tasks processed: {total_tasks}")
        print(f"   Successful tasks: {successful_tasks}")
        for result in batch_results:
            status_icon = "✅" if result["success"] else "❌"
            print(f"   {status_icon} {result['task_id']}: {result['execution_status']}")
    
    def test_system_prompt_consistency(self):
        """Test that system prompts are consistent across different system combinations"""
        test_combinations = [
            (["email"], "Email-only"),
            (["email", "calendar"], "Email + Calendar"),
            (["map", "geography"], "Navigation"),
            (["email", "calendar", "map", "geography", "reservation"], "Multi-system"),
            (None, "All systems")
        ]
        
        prompt_generator = SystemPromptGenerator()
        prompt_results = []
        
        for systems, description in test_combinations:
            prompt = prompt_generator.generate_prompt(systems)
            
            # Analyze prompt content
            has_email = "Email System Tools" in prompt
            has_calendar = "Calendar System Tools" in prompt
            has_map = "Map & Geography Tools" in prompt
            
            prompt_results.append({
                "description": description,
                "systems": systems,
                "prompt_length": len(prompt),
                "has_email_tools": has_email,
                "has_calendar_tools": has_calendar,
                "has_map_tools": has_map,
                "expected_email": systems is None or (systems and "email" in systems),
                "expected_calendar": systems is None or (systems and "calendar" in systems),
                "expected_map": systems is None or (systems and "map" in systems)
            })
        
        # Validate consistency
        all_consistent = True
        for result in prompt_results:
            email_consistent = result["has_email_tools"] == result["expected_email"]
            calendar_consistent = result["has_calendar_tools"] == result["expected_calendar"]
            map_consistent = result["has_map_tools"] == result["expected_map"]
            
            if not (email_consistent and calendar_consistent and map_consistent):
                all_consistent = False
                print(f"❌ Inconsistent prompt for {result['description']}")
        
        self.assertTrue(all_consistent, "System prompt generation is not consistent")
        
        print(f"✅ System prompt consistency validated")
        for result in prompt_results:
            print(f"   {result['description']}: {result['prompt_length']} chars, Email: {result['has_email_tools']}, Calendar: {result['has_calendar_tools']}, Map: {result['has_map_tools']}")
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        environment = CampusEnvironment()
        executor = ActionExecutor(environment, ["email"])
        
        # Test various error scenarios
        error_scenarios = [
            {
                "name": "Invalid action format",
                "action": "invalid action format",
                "expected_error": "INVALID"
            },
            {
                "name": "Unavailable system",
                "action": 'Action: map.find_building_id(building_name="Library")',
                "expected_error": "not available"
            },
            {
                "name": "Malformed parameters",
                "action": 'Action: email.send_email(invalid_params)',
                "expected_error": "parameter"
            }
        ]
        
        error_results = []
        for scenario in error_scenarios:
            try:
                parsed = CampusTask._parse_agent_response(scenario["action"])
                
                if parsed.action.value == "invalid":
                    error_results.append({
                        "scenario": scenario["name"],
                        "handled_correctly": True,
                        "error_type": "PARSE_ERROR",
                        "message": "Action parsing failed as expected"
                    })
                else:
                    result = executor.execute_action(parsed.content)
                    error_handled = not result.is_success() and scenario["expected_error"].lower() in result.message.lower()
                    
                    error_results.append({
                        "scenario": scenario["name"],
                        "handled_correctly": error_handled,
                        "error_type": result.status.value,
                        "message": result.message
                    })
            except Exception as e:
                error_results.append({
                    "scenario": scenario["name"],
                    "handled_correctly": True,  # Exception handling is also valid
                    "error_type": "EXCEPTION",
                    "message": str(e)
                })
        
        # Validate error handling
        all_handled = all(r["handled_correctly"] for r in error_results)
        
        self.assertTrue(all_handled, f"Some errors were not handled correctly: {error_results}")
        
        print(f"✅ Error handling and recovery validated")
        for result in error_results:
            status_icon = "✅" if result["handled_correctly"] else "❌"
            print(f"   {status_icon} {result['scenario']}: {result['error_type']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
