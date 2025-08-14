#!/usr/bin/env python3
"""
Quick test for English validation fix
"""

import sys
import os

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'LifelongAgentBench-main', 'src')
sys.path.insert(0, src_path)

def test_english_validation():
    """Test the fixed English validation"""
    print("🌍 Testing Fixed English Validation:")
    print("=" * 50)
    
    try:
        from tasks.instance.campus_life_bench.tools import validate_english_only, ensure_english_message
        
        # Test valid English messages
        valid_messages = [
            "Email sent successfully to recipient",
            "Building found: Grand Central Library",
            "Navigation completed to target location",
            "Event added to calendar successfully",
            "Hello World! 123",
            "Test@email.com with symbols: ()[]{}\"'-_@#$%^&*+=<>/\\|`~"
        ]
        
        print("Testing valid English messages:")
        all_valid_passed = True
        for msg in valid_messages:
            is_valid = validate_english_only(msg)
            status = "✅" if is_valid else "❌"
            print(f"   {status} '{msg[:40]}...'")
            if not is_valid:
                all_valid_passed = False
        
        # Test invalid messages (should be rejected)
        invalid_messages = [
            "邮件发送成功",  # Chinese
            "Correo enviado exitosamente",  # Spanish with ó
            "Café",  # French with é
            "Naïve",  # English word with diacritic
            "résumé",  # French word commonly used in English but with accents
            "piñata",  # Spanish word with ñ
        ]
        
        print("\nTesting invalid messages (should be rejected):")
        all_invalid_rejected = True
        for msg in invalid_messages:
            is_valid = validate_english_only(msg)
            should_be_rejected = not is_valid
            status = "✅" if should_be_rejected else "❌"
            print(f"   {status} '{msg}' -> {'Rejected' if should_be_rejected else 'Incorrectly accepted'}")
            if not should_be_rejected:
                all_invalid_rejected = False
        
        # Test ensure_english_message function
        print("\nTesting ensure_english_message function:")
        try:
            # Valid message should pass
            result1 = ensure_english_message("Valid English message")
            print(f"   ✅ Valid message passed: '{result1}'")
            
            # Invalid message should raise exception
            try:
                result2 = ensure_english_message("Invalid message with ñ")
                print(f"   ❌ Invalid message should have been rejected: '{result2}'")
                all_invalid_rejected = False
            except Exception as e:
                print(f"   ✅ Invalid message correctly rejected: {str(e)}")
                
        except Exception as e:
            print(f"   ❌ Error testing ensure_english_message: {str(e)}")
            return False
        
        # Overall result
        overall_success = all_valid_passed and all_invalid_rejected
        print(f"\n📊 English validation test: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print(f"   Valid messages: {'✅' if all_valid_passed else '❌'}")
        print(f"   Invalid messages rejected: {'✅' if all_invalid_rejected else '❌'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ English validation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the English validation test"""
    print("🚀 English Validation Fix Test")
    print("=" * 40)
    
    success = test_english_validation()
    
    if success:
        print("\n🎉 English validation is now working correctly!")
    else:
        print("\n⚠️  English validation still has issues.")

if __name__ == "__main__":
    main()
