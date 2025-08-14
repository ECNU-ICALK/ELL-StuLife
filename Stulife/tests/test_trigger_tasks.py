"""
Test cases for trigger task handling in CampusLifeBench
Tests both "仅做trigger" tasks and "触发trigger" tasks
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Import the task class
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
from typings import Session, SessionEvaluationOutcome, SessionMetricCalculationPartial, SampleStatus, SessionEvaluationRecord, TaskName
from factories.chat_history_item import ChatHistoryItemFactory


class TestTriggerTasks(unittest.TestCase):
    """Test trigger task handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_data_dir = tempfile.mkdtemp()
        self.task = None
        
    def tearDown(self):
        """Clean up test environment"""
        if self.task:
            try:
                self.task._release()
            except:
                pass
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.test_data_dir, ignore_errors=True)
    
    def create_test_task_data(self, tasks_data):
        """Create test task data file"""
        tasks_file = Path(self.test_data_dir) / "test_tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, indent=2)
        return tasks_file
    
    def test_trigger_task_exclusion_from_metrics(self):
        """Test that trigger tasks are excluded from metric calculation"""
        # Create test data with both trigger and regular tasks
        tasks_data = {
            "regular_task": {
                "task_id": "regular_001",
                "task_type": "email_sending",
                "is_trigger": False,
                "instruction": "Send an email to advisor",
                "require_time": None,
                "require_place": None,
                "source_building_id": None,
                "world_state_change": [],
                "available_systems": ["email"],
                "details": {},
                "ground_truth": {"recipient": "advisor@university.edu"}
            },
            "trigger_task": {
                "task_id": "trigger_001", 
                "task_type": "multi_system",
                "is_trigger": True,
                "instruction": "",
                "require_time": "Week 1, Monday, 09:00",
                "require_place": None,
                "source_building_id": None,
                "world_state_change": [],
                "available_systems": ["email", "calendar"],
                "details": {},
                "ground_truth": {}
            }
        }
        
        tasks_file = self.create_test_task_data(tasks_data)
        
        # Create task instance
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            mock_factory = Mock(spec=ChatHistoryItemFactory)
            self.task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(tasks_file.parent)
            )
            
            # Manually set dataset
            dataset = {}
            for key, data in tasks_data.items():
                dataset[key] = CampusDatasetItem(**data)
            self.task._set_dataset(dataset)
        
        # Create mock session partials
        session_partials = [
            SessionMetricCalculationPartial(
                sample_index="regular_task",
                sample_status=SampleStatus.COMPLETED,
                evaluation_record=SessionEvaluationRecord(outcome=SessionEvaluationOutcome.CORRECT)
            ),
            SessionMetricCalculationPartial(
                sample_index="trigger_task", 
                sample_status=SampleStatus.COMPLETED,
                evaluation_record=SessionEvaluationRecord(outcome=SessionEvaluationOutcome.UNKNOWN)
            )
        ]
        
        # Calculate metrics
        metrics = self.task.calculate_metric(session_partials)
        
        # Verify trigger task is excluded
        self.assertEqual(metrics["trigger_info"]["total_trigger_tasks"], 1.0)
        self.assertEqual(metrics["trigger_info"]["regular_tasks_evaluated"], 1.0)
        self.assertEqual(metrics["overall"]["basic"]["session_count"], 1.0)  # Only regular task counted
    
    def test_trigger_task_evaluation_skip(self):
        """Test that trigger tasks skip evaluation in _complete method"""
        # Create trigger task data
        task_data = {
            "task_id": "trigger_001",
            "task_type": "multi_system", 
            "is_trigger": True,
            "instruction": "",
            "require_time": "Week 1, Monday, 09:00",
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "available_systems": ["email"],
            "details": {},
            "ground_truth": {}
        }
        
        tasks_file = self.create_test_task_data({"trigger_task": task_data})
        
        # Create task instance
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            mock_factory = Mock(spec=ChatHistoryItemFactory)
            self.task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(tasks_file.parent)
            )
            
            # Set dataset
            dataset = {"trigger_task": CampusDatasetItem(**task_data)}
            self.task._set_dataset(dataset)
            self.task.current_sample_index = "trigger_task"
        
        # Create mock session
        session = Mock(spec=Session)
        session.evaluation_record = SessionEvaluationRecord()
        
        # Call _complete method
        self.task._complete(session)
        
        # Verify evaluation was skipped
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.UNKNOWN)
        self.assertTrue(session.evaluation_record.detail_dict["is_trigger_task"])
        self.assertTrue(session.evaluation_record.detail_dict["skip_evaluation"])
    
    def test_empty_instruction_handling(self):
        """Test handling of empty instruction for trigger tasks"""
        # Create task with empty instruction and require_time
        task_data = {
            "task_id": "empty_instruction_001",
            "task_type": "multi_system",
            "is_trigger": False,  # Not a trigger task, but has empty instruction
            "instruction": "",
            "require_time": "Week 1, Monday, 14:00",
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "available_systems": ["email"],
            "details": {},
            "ground_truth": {}
        }
        
        tasks_file = self.create_test_task_data({"empty_task": task_data})
        
        # Create task instance
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            mock_factory = Mock(spec=ChatHistoryItemFactory)
            self.task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(tasks_file.parent)
            )
            
            # Set dataset
            dataset = {"empty_task": CampusDatasetItem(**task_data)}
            self.task._set_dataset(dataset)
            self.task.current_sample_index = "empty_task"
        
        current_item = self.task._get_current_dataset_item()
        
        # Test _get_instruction_content method
        instruction_content = self.task._get_instruction_content(current_item)
        
        # Verify appropriate substitute message is provided
        self.assertIn("Current time: 14:00", instruction_content)
        self.assertIn("You may take actions based on your schedule", instruction_content)
    
    def test_regular_instruction_unchanged(self):
        """Test that regular instructions are not modified"""
        # Create task with normal instruction
        task_data = {
            "task_id": "regular_001",
            "task_type": "email_sending",
            "is_trigger": False,
            "instruction": "Send an email to your advisor asking about office hours.",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "available_systems": ["email"],
            "details": {},
            "ground_truth": {}
        }
        
        tasks_file = self.create_test_task_data({"regular_task": task_data})
        
        # Create task instance
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            mock_factory = Mock(spec=ChatHistoryItemFactory)
            self.task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(tasks_file.parent)
            )
            
            # Set dataset
            dataset = {"regular_task": CampusDatasetItem(**task_data)}
            self.task._set_dataset(dataset)
            self.task.current_sample_index = "regular_task"
        
        current_item = self.task._get_current_dataset_item()
        
        # Test _get_instruction_content method
        instruction_content = self.task._get_instruction_content(current_item)
        
        # Verify original instruction is returned unchanged
        self.assertEqual(instruction_content, "Send an email to your advisor asking about office hours.")


if __name__ == '__main__':
    unittest.main()
