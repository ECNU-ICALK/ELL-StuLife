#!/usr/bin/env python3
"""
Test system prompt generation
"""

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator

def test_system_prompt():
    """Test system prompt generation"""
    
    try:
        print("🔍 Testing system prompt generation...")
        
        generator = SystemPromptGenerator()
        
        # Test with email and reservation systems
        available_systems = ["email", "reservation", "map", "geography"]
        
        prompt = generator.generate_prompt(available_systems)
        
        print("✅ System prompt generated successfully!")
        print("📝 System prompt:")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        
        # Check if prompt contains expected elements
        if "Action:" in prompt and "tool_name" in prompt:
            print("✅ Prompt contains action format instructions")
            return True
        else:
            print("❌ Prompt missing action format instructions")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_system_prompt()
