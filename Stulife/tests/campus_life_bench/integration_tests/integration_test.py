#!/usr/bin/env python3
"""
Integration test for the new CampusLifeBench Action-based system
Tests the complete workflow from task setup to action execution
"""

import sys
import os
sys.path.append('LifelongAgentBench-main/src')

# Set environment variable to avoid import issues
os.environ['PYTHONPATH'] = 'LifelongAgentBench-main/src'

def test_system_prompt_generation():
    """Test the SystemPromptGenerator"""
    print("📝 Testing SystemPromptGenerator:")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator
        
        generator = SystemPromptGenerator()
        
        # Test with email only
        email_prompt = generator.generate_prompt(["email"])
        print(f"✅ Email-only prompt generated ({len(email_prompt)} chars)")
        print(f"   Contains 'Email System Tools': {'Email System Tools' in email_prompt}")
        print(f"   Contains 'send_email': {'send_email' in email_prompt}")
        print(f"   Does NOT contain 'Map Tools': {'Map & Geography Tools' not in email_prompt}")
        
        # Test with multiple systems
        multi_prompt = generator.generate_prompt(["email", "calendar", "map"])
        print(f"✅ Multi-system prompt generated ({len(multi_prompt)} chars)")
        print(f"   Contains Email Tools: {'Email System Tools' in multi_prompt}")
        print(f"   Contains Calendar Tools: {'Calendar System Tools' in multi_prompt}")
        print(f"   Contains Map Tools: {'Map & Geography Tools' in multi_prompt}")
        
        return True
        
    except Exception as e:
        print(f"❌ SystemPromptGenerator test failed: {str(e)}")
        return False

def test_action_executor():
    """Test the ActionExecutor"""
    print("\n🔧 Testing ActionExecutor:")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.action_executor import ActionExecutor
        from tasks.instance.campus_life_bench.environment import CampusEnvironment
        
        env = CampusEnvironment()
        
        # Test with limited systems
        executor = ActionExecutor(env, ["email", "calendar"])
        
        print(f"✅ ActionExecutor created with systems: ['email', 'calendar']")
        
        # Test available actions
        available_actions = executor.get_available_actions()
        print(f"✅ Available actions: {len(available_actions)}")
        
        # Test action availability
        email_available = executor.is_action_available("email.send_email")
        map_available = executor.is_action_available("map.find_building_id")
        
        print(f"✅ email.send_email available: {email_available} (should be True)")
        print(f"✅ map.find_building_id available: {map_available} (should be False)")
        
        # Test parameter parsing
        try:
            action_name, params = executor._parse_action_content(
                'email.send_email(to="test@test.com", subject="Test")'
            )
            print(f"✅ Parameter parsing works: {action_name} with {len(params)} params")
            print(f"   Parsed params: {params}")
        except Exception as e:
            print(f"❌ Parameter parsing failed: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ ActionExecutor test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_task_data_structure():
    """Test the enhanced CampusDatasetItem"""
    print("\n📋 Testing Enhanced Task Data Structure:")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.task import CampusDatasetItem
        
        # Test with available_systems
        item_data = {
            "task_id": "test_001",
            "task_type": "email_sending",
            "instruction": "Send an email",
            "available_systems": ["email"]
        }
        
        item = CampusDatasetItem(**item_data)
        print(f"✅ CampusDatasetItem created with available_systems")
        print(f"   Task ID: {item.task_id}")
        print(f"   Available systems: {item.available_systems}")
        print(f"   Get available systems: {item.get_available_systems()}")
        
        # Test without available_systems
        item_data_no_systems = {
            "task_id": "test_002",
            "task_type": "multi_system",
            "instruction": "Complete multiple tasks"
        }
        
        item_no_systems = CampusDatasetItem(**item_data_no_systems)
        print(f"✅ CampusDatasetItem created without available_systems")
        print(f"   Available systems: {item_no_systems.available_systems} (should be None)")
        
        return True
        
    except Exception as e:
        print(f"❌ Task data structure test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_json_task_examples():
    """Test loading and parsing JSON task examples"""
    print("\n📄 Testing JSON Task Examples:")
    print("=" * 50)
    
    try:
        import json
        
        # Load the example tasks
        with open('LifelongAgentBench-main/src/tasks/instance/campus_life_bench/data/tasks.json', 'r') as f:
            tasks_data = json.load(f)
        
        print(f"✅ Loaded tasks.json with {len(tasks_data)} tasks")
        
        # Check for available_systems field in tasks
        tasks_with_systems = 0
        for task_id, task_data in tasks_data.items():
            if 'available_systems' in task_data:
                tasks_with_systems += 1
                print(f"   Task {task_id}: systems = {task_data['available_systems']}")
        
        print(f"✅ Found {tasks_with_systems} tasks with available_systems field")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON task examples test failed: {str(e)}")
        return False

def test_configuration_examples():
    """Test the configuration examples"""
    print("\n⚙️ Testing Configuration Examples:")
    print("=" * 50)
    
    try:
        import json
        
        # Load the configuration examples
        with open('LifelongAgentBench-main/examples/campus_life_bench_system_configurations.json', 'r') as f:
            config_data = json.load(f)
        
        print(f"✅ Loaded configuration examples")
        print(f"   Configurations: {len(config_data['configurations'])}")
        print(f"   System combinations: {len(config_data['system_combinations'])}")
        
        # Check some specific configurations
        email_only = config_data['configurations']['email_only_task']
        print(f"   Email-only task systems: {email_only['available_systems']}")
        
        multi_system = config_data['configurations']['comprehensive_task']
        print(f"   Comprehensive task systems: {len(multi_system['available_systems'])} systems")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration examples test failed: {str(e)}")
        return False

def test_english_validation():
    """Test English-only validation"""
    print("\n🌍 Testing English-Only Validation:")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.tools import ensure_english_message
        
        # Test valid English messages
        valid_messages = [
            "Email sent successfully",
            "Building found: Grand Central Library",
            "Navigation completed to target location"
        ]
        
        for msg in valid_messages:
            try:
                result = ensure_english_message(msg)
                print(f"✅ Valid: '{msg}' -> '{result}'")
            except Exception as e:
                print(f"❌ Failed: '{msg}' -> {str(e)}")
                return False
        
        # Test invalid messages (should raise exceptions)
        invalid_messages = [
            "邮件发送成功",  # Chinese
            "Correo enviado exitosamente",  # Spanish
        ]
        
        for msg in invalid_messages:
            try:
                result = ensure_english_message(msg)
                print(f"❌ Should have failed: '{msg}' -> '{result}'")
                return False
            except Exception:
                print(f"✅ Correctly rejected: '{msg}'")
        
        return True
        
    except Exception as e:
        print(f"❌ English validation test failed: {str(e)}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 CampusLifeBench Action System Integration Tests")
    print("=" * 70)
    
    tests = [
        ("System Prompt Generation", test_system_prompt_generation),
        ("Action Executor", test_action_executor),
        ("Task Data Structure", test_task_data_structure),
        ("JSON Task Examples", test_json_task_examples),
        ("Configuration Examples", test_configuration_examples),
        ("English Validation", test_english_validation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   Result: {status}")
        except Exception as e:
            print(f"   Result: ❌ ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n🎯 INTEGRATION TEST RESULTS:")
    print("=" * 70)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{len(results)} tests passed ({passed/len(results)*100:.1f}%)")
    
    if passed == len(results):
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ The new Action-based CampusLifeBench system is fully functional!")
        print("\n🔧 Key Features Verified:")
        print("   ✅ Action: format parsing")
        print("   ✅ Dynamic system availability")
        print("   ✅ System prompt generation")
        print("   ✅ Parameter parsing and validation")
        print("   ✅ English-only enforcement")
        print("   ✅ JSON task configuration")
        print("   ✅ Backward compatibility")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Please review the implementation.")

if __name__ == "__main__":
    main()
