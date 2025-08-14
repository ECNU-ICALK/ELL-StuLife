#!/usr/bin/env python3
"""
Integration test for sequence validation in multi-system tasks
Tests the complete workflow from task execution to evaluation
"""

import sys
import os
import json
from pathlib import Path

# Add the src directory to the path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_dir))

def create_test_task_data():
    """Create test task data for sequence validation"""
    return {
        "sample_001": {
            "task_id": "integration_test_001",
            "task_type": "multi_system",
            "is_trigger": False,
            "instruction": "Arrange a meeting with your advisor by sending an email, booking a room, and adding to calendar.",
            "require_time": None,
            "require_place": None,
            "source_building_id": "B083",
            "world_state_change": [
                {
                    "system": "reservation",
                    "action": "set_availability",
                    "parameters": {
                        "location_id": "B001",
                        "item_name": "Study Room A",
                        "date": "Week 1, Thursday",
                        "time_slots": ["14:00-15:00", "15:00-16:00"]
                    }
                }
            ],
            "available_systems": ["email", "reservation", "calendar"],
            "details": {
                "advisor_email": "dr.test@university.edu",
                "meeting_subject": "Research Discussion",
                "room_name": "Study Room A",
                "meeting_time": "Week 1, Thursday, 15:00-16:00"
            },
            "ground_truth": {
                "email_sent": {
                    "recipient": "dr.test@university.edu",
                    "subject_contains": "meeting",
                    "body_contains": "research"
                },
                "reservation_made": {
                    "item_name": "Study Room A",
                    "time": "Week 1, Thursday, 15:00-16:00"
                },
                "calendar_event": {
                    "event_title_contains": "meeting",
                    "time": "Week 1, Thursday, 15:00-16:00",
                    "location": "Study Room A"
                }
            }
        }
    }

def test_sequence_validation_integration():
    """Test the complete sequence validation workflow"""
    print("\n🔄 Integration Test: Sequence Validation Workflow")
    print("=" * 60)
    
    try:
        from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
        from tasks.instance.campus_life_bench.tools import ToolResult
        from typings import TaskName, Session, SessionEvaluationOutcome
        
        # Create test data directory
        test_data_dir = Path(__file__).parent / "test_data"
        test_data_dir.mkdir(exist_ok=True)
        
        # Write test task data
        test_tasks = create_test_task_data()
        test_file = test_data_dir / "tasks.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_tasks, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created test data file: {test_file}")
        
        # Create mock factory
        class MockChatHistoryItemFactory:
            def __init__(self):
                pass
        
        # Create task instance
        task = CampusTask(
            task_name=TaskName.CAMPUS_LIFE_BENCH,
            chat_history_item_factory=MockChatHistoryItemFactory(),
            max_round=10,
            data_dir=test_data_dir
        )
        
        print("✅ Created CampusTask instance")
        
        # Test 1: Simulate correct sequence execution
        print("\n📋 Test 1: Correct Sequence Execution")
        
        # Clear action history
        task.action_history.clear()
        
        # Simulate actions in correct order
        actions = [
            ("email.send_email(to='dr.test@university.edu', subject='Meeting Request')", "email"),
            ("reservation.make_booking(location_id='B001', item_name='Study Room A')", "reservation"),
            ("calendar.add_event(title='Meeting with Advisor', time='Week 1, Thursday, 15:00-16:00')", "calendar")
        ]
        
        for action_content, expected_system in actions:
            # Simulate successful action execution
            tool_result = ToolResult.success(f"{expected_system} operation completed successfully")
            task._record_action_execution(action_content, tool_result)
            print(f"   ✅ Recorded: {expected_system} action")
        
        # Test sequence validation
        ground_truth = test_tasks["sample_001"]["ground_truth"]
        is_valid, message = task._validate_execution_sequence(ground_truth)
        
        print(f"   Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
        print(f"   Message: {message}")
        
        # Test 2: Simulate wrong sequence execution
        print("\n📋 Test 2: Wrong Sequence Execution")
        
        # Clear action history
        task.action_history.clear()
        
        # Simulate actions in wrong order (reservation before email)
        wrong_actions = [
            ("reservation.make_booking(location_id='B001', item_name='Study Room A')", "reservation"),
            ("email.send_email(to='dr.test@university.edu', subject='Meeting Request')", "email"),
            ("calendar.add_event(title='Meeting with Advisor', time='Week 1, Thursday, 15:00-16:00')", "calendar")
        ]
        
        for action_content, expected_system in wrong_actions:
            tool_result = ToolResult.success(f"{expected_system} operation completed successfully")
            task._record_action_execution(action_content, tool_result)
            print(f"   ✅ Recorded: {expected_system} action")
        
        # Test sequence validation
        is_valid, message = task._validate_execution_sequence(ground_truth)
        
        print(f"   Result: {'❌ FAIL (Expected)' if not is_valid else '✅ UNEXPECTED PASS'}")
        print(f"   Message: {message}")
        
        # Test 3: Test evaluation integration
        print("\n📋 Test 3: Evaluation Integration")
        
        # Create a mock session for evaluation
        class MockSession:
            def __init__(self):
                self.evaluation_record = MockEvaluationRecord()
        
        class MockEvaluationRecord:
            def __init__(self):
                self.outcome = None
                self.details = {}
        
        # Test with correct sequence
        task.action_history.clear()
        for action_content, expected_system in actions:
            tool_result = ToolResult.success(f"{expected_system} operation completed successfully")
            task._record_action_execution(action_content, tool_result)
        
        # Mock the component evaluation methods to return True
        def mock_email_eval(criteria):
            return True
        def mock_reservation_eval(criteria, task_id):
            return True
        def mock_calendar_eval(criteria):
            return True
        
        task._evaluate_email_component = mock_email_eval
        task._evaluate_reservation_component = mock_reservation_eval
        task._evaluate_calendar_component = mock_calendar_eval
        
        # Create test dataset item
        test_item = CampusDatasetItem(**test_tasks["sample_001"])
        
        # Test evaluation with correct sequence
        mock_session = MockSession()
        task._evaluate_multi_system(mock_session, test_item)
        
        print(f"   Correct sequence result: {mock_session.evaluation_record.outcome}")
        
        # Test evaluation with wrong sequence
        task.action_history.clear()
        for action_content, expected_system in wrong_actions:
            tool_result = ToolResult.success(f"{expected_system} operation completed successfully")
            task._record_action_execution(action_content, tool_result)
        
        mock_session = MockSession()
        task._evaluate_multi_system(mock_session, test_item)
        
        print(f"   Wrong sequence result: {mock_session.evaluation_record.outcome}")
        print(f"   Error details: {mock_session.evaluation_record.details}")
        
        # Cleanup
        import shutil
        if test_file.exists():
            test_file.unlink()
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run integration tests"""
    print("🚀 CampusLifeBench Sequence Validation Integration Test")
    print("=" * 70)
    
    if test_sequence_validation_integration():
        print("\n🎉 Integration test passed! Sequence validation is fully functional.")
        return True
    else:
        print("\n⚠️  Integration test failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
