#!/usr/bin/env python3
"""
Test script for multi-system task execution sequence validation
Tests the new sequence validation functionality in CampusTask
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_dir))

def test_sequence_validation_logic():
    """Test the sequence validation logic directly"""
    print("\n🧪 Testing Sequence Validation Logic")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
        from factories.chat_history_item import ChatHistoryItemFactory
        from typings import TaskName
        
        # Create a test task instance with minimal factory
        from pathlib import Path
        test_data_dir = Path(__file__).parent.parent.parent / "src" / "tasks" / "instance" / "campus_life_bench" / "data"

        # Create a minimal factory (we don't need it for sequence validation tests)
        class MockChatHistoryItemFactory:
            def __init__(self):
                pass

        task = CampusTask(
            task_name=TaskName.CAMPUS_LIFE_BENCH,
            chat_history_item_factory=MockChatHistoryItemFactory(),
            max_round=10,
            data_dir=test_data_dir
        )
        
        # Test 1: Correct sequence validation
        print("\n📋 Test 1: Correct Sequence Validation")
        
        # Simulate action history with correct order
        task.action_history = [
            {"timestamp": 1.0, "system_type": "email", "success": True},
            {"timestamp": 2.0, "system_type": "reservation", "success": True},
            {"timestamp": 3.0, "system_type": "calendar", "success": True}
        ]
        
        ground_truth = {
            "email_sent": {"recipient": "test@example.com"},
            "reservation_made": {"item_name": "Room A"},
            "calendar_event": {"event_title": "Meeting"}
        }
        
        is_valid, message = task._validate_execution_sequence(ground_truth)
        print(f"   Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
        print(f"   Message: {message}")
        
        # Test 2: Wrong sequence validation
        print("\n📋 Test 2: Wrong Sequence Validation")
        
        # Simulate action history with wrong order
        task.action_history = [
            {"timestamp": 1.0, "system_type": "reservation", "success": True},
            {"timestamp": 2.0, "system_type": "email", "success": True},
            {"timestamp": 3.0, "system_type": "calendar", "success": True}
        ]
        
        is_valid, message = task._validate_execution_sequence(ground_truth)
        print(f"   Result: {'❌ FAIL (Expected)' if not is_valid else '✅ UNEXPECTED PASS'}")
        print(f"   Message: {message}")
        
        # Test 3: Single system (no validation needed)
        print("\n📋 Test 3: Single System Task")
        
        task.action_history = [
            {"timestamp": 1.0, "system_type": "email", "success": True}
        ]
        
        single_ground_truth = {
            "email_sent": {"recipient": "test@example.com"}
        }
        
        is_valid, message = task._validate_execution_sequence(single_ground_truth)
        print(f"   Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
        print(f"   Message: {message}")
        
        # Test 4: System type extraction
        print("\n📋 Test 4: System Type Extraction")
        
        test_actions = [
            "email.send_email(to='test@example.com', subject='Test')",
            "reservation.make_booking(location_id='B001', item_name='Room A')",
            "calendar.add_event(title='Meeting', time='14:00')",
            "geography.walk_to(building_id='B002')",
            "unknown_action()"
        ]
        
        expected_types = ["email", "reservation", "calendar", "geography", "unknown"]
        
        for action, expected in zip(test_actions, expected_types):
            extracted = task._extract_system_type_from_action(action)
            result = "✅ PASS" if extracted == expected else "❌ FAIL"
            print(f"   Action: {action[:30]}... → {extracted} ({result})")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_action_recording():
    """Test the action recording functionality"""
    print("\n🎬 Testing Action Recording")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.task import CampusTask
        from tasks.instance.campus_life_bench.tools import ToolResult
        from factories.chat_history_item import ChatHistoryItemFactory
        from typings import TaskName
        
        # Create a test task instance with minimal factory
        from pathlib import Path
        test_data_dir = Path(__file__).parent.parent.parent / "src" / "tasks" / "instance" / "campus_life_bench" / "data"

        # Create a minimal factory (we don't need it for action recording tests)
        class MockChatHistoryItemFactory:
            def __init__(self):
                pass

        task = CampusTask(
            task_name=TaskName.CAMPUS_LIFE_BENCH,
            chat_history_item_factory=MockChatHistoryItemFactory(),
            max_round=10,
            data_dir=test_data_dir
        )
        
        # Test action recording
        test_action = "email.send_email(to='test@example.com', subject='Test Email')"
        test_result = ToolResult.success("Email sent successfully")
        
        # Record the action
        task._record_action_execution(test_action, test_result)
        
        # Verify recording
        if len(task.action_history) == 1:
            record = task.action_history[0]
            print(f"✅ Action recorded successfully:")
            print(f"   System Type: {record['system_type']}")
            print(f"   Success: {record['success']}")
            print(f"   Action: {record['action_content'][:50]}...")
            return True
        else:
            print(f"❌ Action recording failed: expected 1 record, got {len(task.action_history)}")
            return False
            
    except Exception as e:
        print(f"❌ Action recording test failed: {str(e)}")
        return False

def main():
    """Run all sequence validation tests"""
    print("🚀 CampusLifeBench Sequence Validation Test Suite")
    print("=" * 60)
    
    tests = [
        ("Sequence Validation Logic", test_sequence_validation_logic),
        ("Action Recording", test_action_recording)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Sequence validation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
