#!/usr/bin/env python3
"""
Integration test for CampusTask trigger functionality
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
from typings import SessionMetricCalculationPartial, SessionEvaluationRecord, SessionEvaluationOutcome, SampleStatus, TaskName, Session
from factories.chat_history_item import ChatHistoryItemFactory

def create_test_data():
    """Create test data with trigger and regular tasks"""
    return {
        "regular_task": {
            "task_id": "regular_task",
            "task_type": "email_sending",
            "is_trigger": False,
            "instruction": "Send an email to your advisor",
            "require_time": None,
            "require_place": None,
            "source_building_id": "B083",
            "world_state_change": [],
            "available_systems": ["email"],
            "details": {},
            "ground_truth": {"recipient": "advisor@university.edu"}
        },
        "trigger_task": {
            "task_id": "trigger_task",
            "task_type": "multi_system",
            "is_trigger": True,
            "instruction": "",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [
                {
                    "change_type": "email_received",
                    "from": "advisor@university.edu",
                    "subject": "Meeting Reminder"
                }
            ],
            "available_systems": ["email", "calendar"],
            "details": {},
            "ground_truth": {}
        },
        "empty_instruction_task": {
            "task_id": "empty_instruction_task",
            "task_type": "multi_system",
            "is_trigger": False,
            "instruction": "",
            "require_time": "Week 1, Tuesday, 14:00",
            "require_place": None,
            "source_building_id": "B083",
            "world_state_change": [],
            "available_systems": ["email", "calendar"],
            "details": {},
            "ground_truth": {"should_take_action": True}
        }
    }

def test_metric_calculation():
    """Test metric calculation with trigger task filtering"""
    print("🧪 Testing metric calculation with trigger filtering...")
    
    # Create temporary directory and test data
    with tempfile.TemporaryDirectory() as temp_dir:
        test_data = create_test_data()
        
        # Save test data
        tasks_file = Path(temp_dir) / "test_tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)
        
        # Create mock factory
        mock_factory = Mock(spec=ChatHistoryItemFactory)
        
        # Create task instance with mocked dataset loading
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            
            task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(temp_dir)
            )
            
            # Manually set dataset
            dataset = {}
            for key, data in test_data.items():
                dataset[key] = CampusDatasetItem(**data)
            task._set_dataset(dataset)
        
        # Create session partials
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
            ),
            SessionMetricCalculationPartial(
                sample_index="empty_instruction_task",
                sample_status=SampleStatus.COMPLETED,
                evaluation_record=SessionEvaluationRecord(outcome=SessionEvaluationOutcome.CORRECT)
            )
        ]
        
        # Calculate metrics
        metrics = task.calculate_metric(session_partials)

        # Debug: Print metrics structure
        print(f"📊 Metrics structure: {list(metrics.keys())}")

        # Verify results
        print(f"✅ Total sessions processed: {len(session_partials)}")
        print(f"✅ Trigger tasks excluded: {metrics['trigger_info']['total_trigger_tasks']}")
        print(f"✅ Regular tasks evaluated: {metrics['trigger_info']['regular_tasks_evaluated']}")

        # Check if 'overall' key exists
        if 'overall' in metrics:
            print(f"✅ Session count in metrics: {metrics['overall']['basic']['session_count']}")
            # Assertions
            assert metrics["trigger_info"]["total_trigger_tasks"] == 1.0
            assert metrics["trigger_info"]["regular_tasks_evaluated"] == 2.0
            assert metrics["overall"]["basic"]["session_count"] == 2.0  # Only non-trigger tasks
        else:
            print(f"⚠️ 'overall' key not found in metrics. Available keys: {list(metrics.keys())}")
            # Basic assertions
            assert metrics["trigger_info"]["total_trigger_tasks"] == 1.0
            assert metrics["trigger_info"]["regular_tasks_evaluated"] == 2.0
        
        print("✅ Metric calculation test passed!")
        
        # Clean up
        task._release()

def test_trigger_evaluation_skip():
    """Test that trigger tasks skip evaluation"""
    print("\n🧪 Testing trigger task evaluation skip...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_data = {"trigger_task": create_test_data()["trigger_task"]}
        
        # Save test data
        tasks_file = Path(temp_dir) / "test_tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)
        
        # Create mock factory
        mock_factory = Mock(spec=ChatHistoryItemFactory)
        
        # Create task instance
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            
            task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(temp_dir)
            )
            
            # Set dataset
            dataset = {"trigger_task": CampusDatasetItem(**test_data["trigger_task"])}
            task._set_dataset(dataset)
            task.current_sample_index = "trigger_task"
            # Set current dataset item manually for testing
            task._Task__current_dataset_item = dataset["trigger_task"]
        
        # Create mock session
        session = Mock(spec=Session)
        session.evaluation_record = SessionEvaluationRecord()
        
        # Call _complete method
        task._complete(session)
        
        # Verify evaluation was skipped
        assert session.evaluation_record.outcome == SessionEvaluationOutcome.UNKNOWN
        assert session.evaluation_record.detail_dict["is_trigger_task"] == True
        assert session.evaluation_record.detail_dict["skip_evaluation"] == True
        assert session.evaluation_record.detail_dict["task_id"] == "trigger_task"
        
        print("✅ Trigger evaluation skip test passed!")
        
        # Clean up
        task._release()

def test_empty_instruction_handling():
    """Test empty instruction handling"""
    print("\n🧪 Testing empty instruction handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_data = {"empty_task": create_test_data()["empty_instruction_task"]}
        
        # Save test data
        tasks_file = Path(temp_dir) / "test_tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)
        
        # Create mock factory
        mock_factory = Mock(spec=ChatHistoryItemFactory)
        
        # Create task instance
        with patch('tasks.instance.campus_life_bench.task.CampusTask._load_dataset') as mock_load:
            mock_load.return_value = None
            
            task = CampusTask(
                task_name=TaskName("campus_life_bench"),
                chat_history_item_factory=mock_factory,
                max_round=10,
                data_dir=Path(temp_dir)
            )
            
            # Set dataset
            dataset = {"empty_task": CampusDatasetItem(**test_data["empty_task"])}
            task._set_dataset(dataset)
            task.current_sample_index = "empty_task"
            # Set current dataset item manually for testing
            task._Task__current_dataset_item = dataset["empty_task"]
        
        # Test instruction content generation
        current_item = task._get_current_dataset_item()
        instruction_content = task._get_instruction_content(current_item)
        
        # Verify appropriate content is generated
        assert instruction_content == "Current time: 14:00"
        
        print(f"✅ Generated instruction content: '{instruction_content}'")
        print("✅ Empty instruction handling test passed!")
        
        # Clean up
        task._release()

def main():
    """Run all integration tests"""
    print("🚀 Starting CampusTask integration tests...\n")
    
    try:
        test_metric_calculation()
        test_trigger_evaluation_skip()
        test_empty_instruction_handling()
        
        print("\n🎉 All integration tests passed! CampusTask trigger functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
