#!/usr/bin/env python3
"""
Simple Test Runner for CampusLifeBench Action System

This script runs a subset of tests to verify the fixes work correctly.
"""

import unittest
import sys
import os
import time
from datetime import datetime

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
sys.path.insert(0, src_path)

from comprehensive_action_test_suite import (
    SingleSystemTests,
    ActionFormatValidationTests,
    TestDataLoader
)


class SimpleTestRunner:
    """Simple test runner for debugging"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def run_basic_tests(self):
        """Run basic tests to verify fixes"""
        print("🚀 Running Basic CampusLifeBench Tests")
        print("=" * 60)
        
        # Test 1: Data loading
        print("\n1️⃣ Testing Data Loading")
        try:
            test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
            data_loader = TestDataLoader(test_data_dir)
            
            # Try to load test data
            single_tests = data_loader.get_test_category("single_system_tests")
            print(f"   ✅ Loaded {len(single_tests)} single system tests")
            
            # Check if we have the corrected test data
            if "email_system_test" in single_tests:
                email_test = single_tests["email_system_test"]
                print(f"   ✅ Email test found: {email_test.get('task_id', 'unknown')}")
                
                # Check if it has the correct structure
                if "details" in email_test:
                    print(f"   ✅ Test data has correct structure with details")
                else:
                    print(f"   ⚠️  Test data missing 'details' field")
            
        except Exception as e:
            print(f"   ❌ Data loading failed: {str(e)}")
            return False
        
        # Test 2: Action format validation
        print("\n2️⃣ Testing Action Format Validation")
        try:
            suite = unittest.TestSuite()
            suite.addTest(ActionFormatValidationTests('test_valid_action_formats'))
            suite.addTest(ActionFormatValidationTests('test_invalid_action_formats'))
            
            runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
            result = runner.run(suite)
            
            if result.wasSuccessful():
                print(f"   ✅ Action format validation tests passed")
            else:
                print(f"   ❌ Action format validation tests failed")
                for failure in result.failures:
                    print(f"      Failure: {failure[1]}")
                for error in result.errors:
                    print(f"      Error: {error[1]}")
                return False
                
        except Exception as e:
            print(f"   ❌ Action format validation failed: {str(e)}")
            return False
        
        # Test 3: Single system test (email only)
        print("\n3️⃣ Testing Single System (Email)")
        try:
            suite = unittest.TestSuite()
            suite.addTest(SingleSystemTests('test_email_system'))
            
            runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
            result = runner.run(suite)
            
            if result.wasSuccessful():
                print(f"   ✅ Email system test passed")
            else:
                print(f"   ❌ Email system test failed")
                for failure in result.failures:
                    print(f"      Failure: {failure[1]}")
                for error in result.errors:
                    print(f"      Error: {error[1]}")
                return False
                
        except Exception as e:
            print(f"   ❌ Email system test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 4: Calendar system test
        print("\n4️⃣ Testing Single System (Calendar)")
        try:
            suite = unittest.TestSuite()
            suite.addTest(SingleSystemTests('test_calendar_system'))
            
            runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
            result = runner.run(suite)
            
            if result.wasSuccessful():
                print(f"   ✅ Calendar system test passed")
            else:
                print(f"   ❌ Calendar system test failed")
                for failure in result.failures:
                    print(f"      Failure: {failure[1]}")
                for error in result.errors:
                    print(f"      Error: {error[1]}")
                return False
                
        except Exception as e:
            print(f"   ❌ Calendar system test failed: {str(e)}")
            return False
        
        return True
    
    def print_summary(self, success: bool):
        """Print test summary"""
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("🎯 BASIC TEST RESULTS SUMMARY")
        print("=" * 60)
        
        if success:
            print(f"✅ All basic tests PASSED!")
            print(f"⏱️  Execution time: {total_time:.2f} seconds")
            print(f"🎉 The fixes are working correctly!")
            print(f"\n📋 Tests completed:")
            print(f"   ✅ Data loading and structure validation")
            print(f"   ✅ Action format parsing validation")
            print(f"   ✅ Email system functionality")
            print(f"   ✅ Calendar system functionality")
        else:
            print(f"❌ Some basic tests FAILED!")
            print(f"⏱️  Execution time: {total_time:.2f} seconds")
            print(f"⚠️  Please review the error messages above")


def main():
    """Main entry point"""
    runner = SimpleTestRunner()
    success = runner.run_basic_tests()
    runner.print_summary(success)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
