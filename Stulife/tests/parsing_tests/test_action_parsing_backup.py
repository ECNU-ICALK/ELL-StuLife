#!/usr/bin/env python3
"""
Test script for the new Action-based system in CampusLifeBench
"""

import sys
sys.path.append('LifelongAgentBench-main/src')

from tasks.instance.campus_life_bench.task import CampusTask
from tasks.instance.campus_life_bench.action_executor import ActionExecutor
from tasks.instance.campus_life_bench.environment import CampusEnvironment
from tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator

def test_action_parsing():
    """Test the new Action parsing functionality"""
    print("🧪 Testing Action Parsing:")
    print("=" * 50)
    
    test_cases = [
        'Action: email.send_email(to="test@test.com", subject="Test", body="Hello")',
        'Action: geography.get_current_location()',
        'Action: finish()',
        'Invalid format without action',
        'Action: map.find_building_id(building_name="Library")',
        '```python\nenv.send_email()\n```',  # Old format should be invalid
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = CampusTask._parse_agent_response(test_case)
            print(f"{i}. Input: {test_case[:60]}...")
            print(f"   Action: {result.action}")
            print(f"   Content: {result.content}")
            print(f"   Status: ✅ Parsed successfully")
        except Exception as e:
            print(f"{i}. Input: {test_case[:60]}...")
            print(f"   Status: ❌ Error: {str(e)}")
        print()

def test_system_availability():
    """Test system availability filtering"""
    print("🔒 Testing System Availability:")
    print("=" * 50)
    
    env = CampusEnvironment()
    
    # Test with limited systems
    limited_systems = ["email", "calendar"]
    executor = ActionExecutor(env, limited_systems)
    
    print(f"Available systems: {limited_systems}")
    print(f"Available actions: {len(executor.get_available_actions())}")
    
    # Test allowed action
    print("\n1. Testing allowed action (email):")
    try:
        result = executor.execute_action('email.send_email(to="test@test.com", subject="Test", body="Hello")')
        print(f"   Result: {result.status} - {result.message[:100]}...")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Test disallowed action
    print("\n2. Testing disallowed action (map):")
    try:
        result = executor.execute_action('map.find_building_id(building_name="Library")')
        print(f"   Result: {result.status} - {result.message}")
    except Exception as e:
        print(f"   Error: {str(e)}")

def test_system_prompt_generation():
    """Test dynamic system prompt generation"""
    print("📝 Testing System Prompt Generation:")
    print("=" * 50)
    
    generator = SystemPromptGenerator()
    
    # Test with all systems
    print("1. Generating prompt with all systems:")
    prompt_all = generator.generate_prompt()
    print(f"   Length: {len(prompt_all)} characters")
    print(f"   Contains Email Tools: {'Email System Tools' in prompt_all}")
    print(f"   Contains Map Tools: {'Map & Geography Tools' in prompt_all}")
    
    # Test with limited systems
    print("\n2. Generating prompt with limited systems (email only):")
    prompt_limited = generator.generate_prompt(["email"])
    print(f"   Length: {len(prompt_limited)} characters")
    print(f"   Contains Email Tools: {'Email System Tools' in prompt_limited}")
    print(f"   Contains Map Tools: {'Map & Geography Tools' in prompt_limited}")

def test_parameter_parsing():
    """Test parameter parsing in actions"""
    print("🔧 Testing Parameter Parsing:")
    print("=" * 50)
    
    env = CampusEnvironment()
    executor = ActionExecutor(env, ["email"])
    
    test_actions = [
        'email.send_email(to="test@test.com", subject="Test Subject")',
        'email.view_inbox(filter_unread=True)',
        'email.send_email(to="user@domain.com", subject="Meeting", body="Let\'s meet tomorrow", cc="boss@domain.com")'
    ]
    
    for i, action in enumerate(test_actions, 1):
        try:
            action_name, params = executor._parse_action_content(action)
            print(f"{i}. Action: {action_name}")
            print(f"   Parameters: {params}")
            print(f"   Status: ✅ Parsed successfully")
        except Exception as e:
            print(f"{i}. Action: {action}")
            print(f"   Status: ❌ Error: {str(e)}")
        print()

def test_english_validation():
    """Test English-only message validation"""
    print("🌍 Testing English-Only Validation:")
    print("=" * 50)
    
    env = CampusEnvironment()
    executor = ActionExecutor(env, ["email"])
    
    # Execute an action and check the result message
    try:
        result = executor.execute_action('email.send_email(to="test@test.com", subject="Test", body="Hello")')
        
        # Check if message contains only English characters
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-:()[]{}\"'")
        is_english = all(char in allowed_chars for char in result.message)
        
        print(f"Result message: {result.message}")
        print(f"English-only validation: {'✅ Passed' if is_english else '❌ Failed'}")
        
    except Exception as e:
        print(f"Error during execution: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 CampusLifeBench Action System Tests")
    print("=" * 60)
    print()
    
    try:
        test_action_parsing()
        print()
        
        test_system_availability()
        print()
        
        test_system_prompt_generation()
        print()
        
        test_parameter_parsing()
        print()
        
        test_english_validation()
        print()
        
        print("🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
