#!/usr/bin/env python3
"""
Debug script for course selection test
"""

import sys
import os

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
sys.path.insert(0, src_path)

from comprehensive_action_test_suite import TestDataLoader, SingleSystemTests
from tasks.instance.campus_life_bench.task import CampusDatasetItem
from tasks.instance.campus_life_bench.action_executor import ActionExecutor
from tasks.instance.campus_life_bench.environment import CampusEnvironment

def debug_course_selection():
    """Debug the course selection test"""
    print("🔍 Debugging Course Selection Test")
    print("=" * 50)
    
    # Load test data
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    data_loader = TestDataLoader(test_data_dir)
    
    try:
        single_tests = data_loader.get_test_category("single_system_tests")
        
        if "course_selection_test" not in single_tests:
            print("❌ course_selection_test not found in test data")
            print(f"Available tests: {list(single_tests.keys())}")
            return
        
        test_data = single_tests["course_selection_test"]
        print(f"✅ Found test data: {test_data['task_id']}")
        
        # Create dataset item
        dataset_item = CampusDatasetItem(**test_data)
        print(f"✅ Created dataset item with systems: {dataset_item.available_systems}")
        
        # Create environment and executor
        environment = CampusEnvironment()
        executor = ActionExecutor(environment, dataset_item.available_systems)
        print(f"✅ Created executor with {len(executor.get_available_actions())} available actions")
        
        # Generate test actions
        details = test_data["details"]
        course_code = details["course_code"]
        test_actions = [
            'Action: course_selection.browse_courses(filters={"department": "Computer Science"})',
            f'Action: draft.add_course(section_id="{course_code}")',
            f'Action: draft.assign_pass(section_id="{course_code}", pass_type="{details["pass_type"]}")'
        ]
        
        print(f"\n📋 Testing {len(test_actions)} actions:")
        
        # Execute each action and show detailed results
        for i, action in enumerate(test_actions, 1):
            print(f"\n{i}. Testing: {action}")
            
            try:
                # Check if action is available
                action_name = action.split('(')[0].replace('Action: ', '')
                is_available = executor.is_action_available(action_name)
                print(f"   Action available: {is_available}")
                
                if not is_available:
                    print(f"   ❌ Action {action_name} not available")
                    print(f"   Available actions: {[a for a in executor.get_available_actions() if action_name.split('.')[0] in a]}")
                    continue
                
                # Parse and execute
                from tasks.instance.campus_life_bench.task import CampusTask
                parsed = CampusTask._parse_agent_response(action)
                print(f"   Parsed action: {parsed.action}")
                
                if parsed.action.value == "execute":
                    result = executor.execute_action(parsed.content)
                    print(f"   Result status: {result.status}")
                    print(f"   Result message: {result.message}")
                    print(f"   Success: {result.is_success()}")
                    
                    if result.data:
                        print(f"   Result data: {result.data}")
                else:
                    print(f"   ❌ Failed to parse action")
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_course_selection()
