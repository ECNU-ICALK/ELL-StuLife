#!/usr/bin/env python3
"""
Test script to verify background data loading functionality
"""

import sys
import os
from pathlib import Path

# Add the LifelongAgentBench source to Python path
sys.path.insert(0, str(Path(__file__).parent / "LifelongAgentBench-main" / "src"))

try:
    from tasks.instance.campus_life_bench.environment import CampusEnvironment
    from tasks.instance.campus_life_bench.task import CampusTask
    from factories.chat_history_item import ChatHistoryItemFactory
    
    def test_background_data_loading():
        """Test loading background data from the new structure"""
        print("🧪 Testing background data loading...")
        
        # Test with background directory
        background_data_dir = Path("任务数据")
        
        try:
            # Initialize CampusEnvironment with background data
            env = CampusEnvironment(data_dir=str(background_data_dir))
            print("✅ CampusEnvironment initialized successfully")
            
            # Test bibliography system
            print("\n📚 Testing bibliography system...")
            result = env.list_chapters("Student Handbook")
            if result.is_success():
                print(f"✅ Bibliography test passed: Found {len(result.data.get('chapters', []))} chapters")
            else:
                print(f"❌ Bibliography test failed: {result.message}")
            
            # Test data system
            print("\n🏫 Testing data system...")
            result = env.list_by_category("Academic & Technological", "club")
            if result.is_success():
                print(f"✅ Data system test passed: Found clubs in category")
            else:
                print(f"❌ Data system test failed: {result.message}")
            
            # Test map system
            print("\n🗺️ Testing map system...")
            result = env.find_building_id("Grand Central Library")
            if result.is_success():
                print(f"✅ Map system test passed: Found building {result.data.get('building_id')}")
            else:
                print(f"❌ Map system test failed: {result.message}")
            
            print("\n🎉 All tests completed!")
            return True
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_task_initialization():
        """Test CampusTask initialization with background data"""
        print("\n🎯 Testing CampusTask initialization...")
        
        try:
            # Create chat history factory
            chat_factory = ChatHistoryItemFactory()
            
            # Initialize CampusTask with background data
            task = CampusTask(
                task_name="test_task",
                chat_history_item_factory=chat_factory,
                max_round=10,
                data_dir=Path("任务数据")
            )
            print("✅ CampusTask initialized successfully")
            
            # Test environment access
            env = task.campus_environment
            result = env.list_chapters("Student Handbook")
            if result.is_success():
                print("✅ Task environment access test passed")
            else:
                print(f"❌ Task environment access test failed: {result.message}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during task testing: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    if __name__ == "__main__":
        print("🚀 Starting background data loading tests...\n")
        
        # Test environment loading
        env_success = test_background_data_loading()
        
        # Test task initialization
        task_success = test_task_initialization()
        
        if env_success and task_success:
            print("\n🎉 All tests passed! Background data loading is working correctly.")
        else:
            print("\n❌ Some tests failed. Please check the implementation.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the LifelongAgentBench source code is available and properly structured.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
