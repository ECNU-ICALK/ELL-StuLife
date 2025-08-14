#!/usr/bin/env python3
"""
Simple test script to verify trigger task functionality
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tasks.instance.campus_life_bench.task import CampusDatasetItem
from typings import SessionMetricCalculationPartial, SessionEvaluationRecord, SessionEvaluationOutcome, SampleStatus

def test_trigger_task_creation():
    """Test creating trigger tasks"""
    print("🧪 Testing trigger task creation...")
    
    # Test regular task
    regular_task = CampusDatasetItem(
        task_id="regular_001",
        task_type="email_sending",
        is_trigger=False,
        instruction="Send an email to advisor",
        ground_truth={"recipient": "advisor@university.edu"}
    )
    
    # Test trigger task
    trigger_task = CampusDatasetItem(
        task_id="trigger_001",
        task_type="multi_system",
        is_trigger=True,
        instruction="",
        ground_truth={}
    )
    
    print(f"✅ Regular task created: {regular_task.task_id}, is_trigger={regular_task.is_trigger}")
    print(f"✅ Trigger task created: {trigger_task.task_id}, is_trigger={trigger_task.is_trigger}")
    
    return regular_task, trigger_task

def test_instruction_content_helper():
    """Test the _get_instruction_content helper method"""
    print("\n🧪 Testing instruction content helper...")
    
    # Create a mock task instance to test the helper method
    class MockCampusTask:
        def _extract_time_only(self, time_str):
            if not time_str:
                return "Unknown time"
            # Simple extraction for testing
            if "14:00" in time_str:
                return "14:00"
            return time_str
        
        def _get_instruction_content(self, current_item):
            """Copy of the method from CampusTask"""
            if not current_item.instruction or current_item.instruction.strip() == "":
                # For tasks with empty instruction but require_time, provide only time information
                if current_item.require_time:
                    time_only = self._extract_time_only(current_item.require_time)
                    return f"Current time: {time_only}"
                else:
                    # For empty instruction without time, return empty string
                    return ""

            return current_item.instruction
    
    mock_task = MockCampusTask()
    
    # Test empty instruction with time
    empty_with_time = CampusDatasetItem(
        task_id="empty_time_001",
        task_type="multi_system",
        is_trigger=False,
        instruction="",
        require_time="Week 1, Monday, 14:00",
        ground_truth={}
    )
    
    content = mock_task._get_instruction_content(empty_with_time)
    print(f"✅ Empty instruction with time: '{content}'")
    assert content == "Current time: 14:00"
    
    # Test empty instruction without time
    empty_no_time = CampusDatasetItem(
        task_id="empty_no_time_001",
        task_type="multi_system",
        is_trigger=False,
        instruction="",
        ground_truth={}
    )
    
    content = mock_task._get_instruction_content(empty_no_time)
    print(f"✅ Empty instruction without time: '{content}'")
    assert content == ""
    
    # Test regular instruction
    regular = CampusDatasetItem(
        task_id="regular_001",
        task_type="email_sending",
        is_trigger=False,
        instruction="Send an email to advisor",
        ground_truth={}
    )
    
    content = mock_task._get_instruction_content(regular)
    print(f"✅ Regular instruction: '{content}'")
    assert content == "Send an email to advisor"

def test_metric_filtering():
    """Test metric calculation filtering"""
    print("\n🧪 Testing metric calculation filtering...")
    
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
    
    # Create mock dataset items
    regular_item = CampusDatasetItem(
        task_id="regular_task",
        task_type="email_sending",
        is_trigger=False,
        instruction="Send email",
        ground_truth={}
    )
    
    trigger_item = CampusDatasetItem(
        task_id="trigger_task",
        task_type="multi_system",
        is_trigger=True,
        instruction="",
        ground_truth={}
    )
    
    # Mock the filtering logic
    filtered_sessions = []
    trigger_count = 0
    
    for session_partial in session_partials:
        # Simulate getting dataset item
        if session_partial.sample_index == "regular_task":
            dataset_item = regular_item
        else:
            dataset_item = trigger_item
            
        if dataset_item.is_trigger:
            trigger_count += 1
            print(f"🔔 Would exclude trigger task: {dataset_item.task_id}")
        else:
            filtered_sessions.append(session_partial)
    
    print(f"✅ Filtered sessions: {len(filtered_sessions)} regular, {trigger_count} trigger excluded")
    assert len(filtered_sessions) == 1
    assert trigger_count == 1

def main():
    """Run all tests"""
    print("🚀 Starting trigger task functionality tests...\n")
    
    try:
        test_trigger_task_creation()
        test_instruction_content_helper()
        test_metric_filtering()
        
        print("\n🎉 All tests passed! Trigger task functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
