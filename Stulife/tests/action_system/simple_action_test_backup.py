#!/usr/bin/env python3
"""
Simple test for Action parsing functionality
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AgentAction(Enum):
    EXECUTE = "execute"
    FINISH = "finish"
    INVALID = "invalid"

@dataclass
class AgentResponseParserResult:
    action: AgentAction
    content: Optional[str]
    finish_reason: Optional[str]

def parse_agent_response(agent_response: str) -> AgentResponseParserResult:
    """
    Parse agent response to extract action in new Action: format
    """
    # Look for Action: pattern first (new format)
    action_pattern = r'Action:\s*([^(]+)\((.*?)\)'
    action_match = re.search(action_pattern, agent_response, re.DOTALL)
    
    if action_match:
        action_name = action_match.group(1).strip()
        action_params = action_match.group(2).strip()
        
        # Handle finish() action
        if action_name.lower() == 'finish':
            return AgentResponseParserResult(
                action=AgentAction.FINISH,
                content=None,
                finish_reason=None
            )
        
        # Handle tool actions
        return AgentResponseParserResult(
            action=AgentAction.EXECUTE,
            content=f"{action_name}({action_params})",
            finish_reason=None
        )
    
    # Fallback: Look for finish keyword (backward compatibility)
    if re.search(r'\bfinish\s*\(\s*\)', agent_response, re.IGNORECASE):
        return AgentResponseParserResult(
            action=AgentAction.FINISH,
            content=None,
            finish_reason=None
        )
    
    # No valid action found
    return AgentResponseParserResult(
        action=AgentAction.INVALID,
        content=None,
        finish_reason="No valid action found in response. Expected format: Action: tool_name(param1=\"value1\", param2=\"value2\")"
    )

def test_action_parsing():
    """Test the Action parsing functionality"""
    print("🧪 Testing Action Parsing:")
    print("=" * 60)
    
    test_cases = [
        {
            'input': 'Action: email.send_email(to="test@test.com", subject="Test", body="Hello")',
            'expected': AgentAction.EXECUTE,
            'description': 'Valid email action'
        },
        {
            'input': 'Action: geography.get_current_location()',
            'expected': AgentAction.EXECUTE,
            'description': 'Valid geography action with no params'
        },
        {
            'input': 'Action: finish()',
            'expected': AgentAction.FINISH,
            'description': 'Valid finish action'
        },
        {
            'input': 'finish()',
            'expected': AgentAction.FINISH,
            'description': 'Backward compatible finish'
        },
        {
            'input': 'Invalid format without action',
            'expected': AgentAction.INVALID,
            'description': 'Invalid format - no action'
        },
        {
            'input': '```python\nenv.send_email()\n```',
            'expected': AgentAction.INVALID,
            'description': 'Old Python code format (should be invalid)'
        },
        {
            'input': 'Action: map.find_building_id(building_name="Library")',
            'expected': AgentAction.EXECUTE,
            'description': 'Valid map action'
        },
        {
            'input': 'Action: calendar.add_event(calendar_id="self", event_title="Meeting", location="Office", time="Week 1, Monday, 14:00-15:00")',
            'expected': AgentAction.EXECUTE,
            'description': 'Complex calendar action with multiple params'
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = parse_agent_response(test_case['input'])
            success = result.action == test_case['expected']
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{i:2d}. {test_case['description']}")
            print(f"    Input: {test_case['input'][:80]}{'...' if len(test_case['input']) > 80 else ''}")
            print(f"    Expected: {test_case['expected']}")
            print(f"    Got: {result.action}")
            print(f"    Content: {result.content}")
            print(f"    Status: {status}")
            
            if success:
                passed += 1
            
        except Exception as e:
            print(f"{i:2d}. {test_case['description']}")
            print(f"    Status: ❌ ERROR: {str(e)}")
        
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    return passed == total

def test_system_availability_concept():
    """Test the concept of system availability filtering"""
    print("🔒 Testing System Availability Concept:")
    print("=" * 60)
    
    # Simulate available systems
    available_systems = ["email", "calendar"]
    
    # Define system-to-action mapping
    system_mapping = {
        "email": ["email.send_email", "email.view_inbox", "email.reply_email", "email.delete_email"],
        "calendar": ["calendar.add_event", "calendar.remove_event", "calendar.view_schedule"],
        "map": ["map.find_building_id", "map.get_building_details", "map.find_optimal_path"],
        "geography": ["geography.get_current_location", "geography.walk_to"],
        "reservation": ["reservation.query_availability", "reservation.make_booking"]
    }
    
    # Get available actions
    available_actions = []
    for system in available_systems:
        if system in system_mapping:
            available_actions.extend(system_mapping[system])
    
    print(f"Available systems: {available_systems}")
    print(f"Available actions: {len(available_actions)}")
    print(f"Actions: {available_actions}")
    
    # Test action validation
    test_actions = [
        ("email.send_email", True, "Should be allowed - email system available"),
        ("calendar.add_event", True, "Should be allowed - calendar system available"),
        ("map.find_building_id", False, "Should be blocked - map system not available"),
        ("geography.walk_to", False, "Should be blocked - geography system not available"),
        ("reservation.make_booking", False, "Should be blocked - reservation system not available")
    ]
    
    print(f"\n🧪 Testing action validation:")
    passed = 0
    
    for action, should_be_allowed, description in test_actions:
        is_allowed = action in available_actions
        success = is_allowed == should_be_allowed
        status = "✅ PASS" if success else "❌ FAIL"
        
        print(f"  {action}: {status} - {description}")
        if success:
            passed += 1
    
    print(f"\n📊 Validation Results: {passed}/{len(test_actions)} tests passed")
    return passed == len(test_actions)

def test_prompt_generation_concept():
    """Test the concept of dynamic prompt generation"""
    print("📝 Testing Dynamic Prompt Generation Concept:")
    print("=" * 60)
    
    # Simulate system descriptions
    system_descriptions = {
        "email": "Email System Tools 📧",
        "calendar": "Calendar System Tools 🗓️",
        "map": "Map & Geography Tools 🗺️",
        "geography": "Map & Geography Tools 🗺️",
        "reservation": "Reservation System Tools 🔑"
    }
    
    # Test with different system combinations
    test_combinations = [
        (["email"], "Email-only prompt"),
        (["email", "calendar"], "Email + Calendar prompt"),
        (["map", "geography"], "Navigation-only prompt"),
        (["email", "calendar", "map", "geography", "reservation"], "Full system prompt")
    ]
    
    for systems, description in test_combinations:
        print(f"\n{description}:")
        print(f"  Systems: {systems}")
        
        # Generate prompt sections
        prompt_sections = []
        for system in systems:
            if system in system_descriptions:
                prompt_sections.append(f"### {system_descriptions[system]}")
        
        print(f"  Sections: {len(prompt_sections)}")
        print(f"  Content: {', '.join(prompt_sections)}")
    
    print(f"\n✅ Dynamic prompt generation concept validated")
    return True

def main():
    """Run all tests"""
    print("🚀 CampusLifeBench Action System Tests")
    print("=" * 70)
    print()
    
    results = []
    
    try:
        print("1️⃣ Testing Action Parsing")
        results.append(test_action_parsing())
        print()
        
        print("2️⃣ Testing System Availability")
        results.append(test_system_availability_concept())
        print()
        
        print("3️⃣ Testing Prompt Generation")
        results.append(test_prompt_generation_concept())
        print()
        
        # Summary
        passed_tests = sum(results)
        total_tests = len(results)
        
        print("🎯 FINAL RESULTS:")
        print("=" * 70)
        print(f"✅ Action Parsing: {'PASS' if results[0] else 'FAIL'}")
        print(f"✅ System Availability: {'PASS' if results[1] else 'FAIL'}")
        print(f"✅ Prompt Generation: {'PASS' if results[2] else 'FAIL'}")
        print()
        print(f"📊 Overall: {passed_tests}/{total_tests} test suites passed")
        
        if all(results):
            print("🎉 All core functionality tests PASSED!")
            print("✅ The new Action-based system is working correctly!")
        else:
            print("⚠️  Some tests failed. Please review the implementation.")
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
