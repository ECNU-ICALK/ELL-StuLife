#!/usr/bin/env python3
"""
Test runner for CampusLifeBench
Runs all unit tests and integration tests
All natural language communications/returns MUST use English only
"""

import unittest
import sys
from pathlib import Path
import argparse

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def run_unit_tests():
    """Run all unit tests"""
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_name):
    """Run a specific test module"""
    print(f"Running specific test: {test_name}")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def validate_requirements():
    """Validate that all requirements are met"""
    print("=" * 60)
    print("VALIDATING REQUIREMENTS")
    print("=" * 60)
    
    requirements_met = True
    
    # Check that all required files exist
    required_files = [
        "src/tasks/instance/campus_life_bench/__init__.py",
        "src/tasks/instance/campus_life_bench/task.py",
        "src/tasks/instance/campus_life_bench/environment.py",
        "src/tasks/instance/campus_life_bench/tools.py",
        "src/tasks/instance/campus_life_bench/data/tasks.json",
        "src/tasks/instance/campus_life_bench/data/map_v1.5.json",
        "src/tasks/instance/campus_life_bench/data/bibliography.json",
        "src/tasks/instance/campus_life_bench/data/campus_data.json",
        "src/tasks/instance/campus_life_bench/data/courses.json",
    ]
    
    base_path = Path(__file__).parent.parent.parent
    
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            print(f"❌ MISSING: {file_path}")
            requirements_met = False
        else:
            print(f"✅ FOUND: {file_path}")
    
    # Check that all subsystems are implemented
    try:
        from tasks.instance.campus_life_bench.systems import (
            WorldTimeSystem, CalendarSystem, MapLookupSystem, GeographySystem,
            ReservationSystem, InformationSystem, CourseSelectionSystem, EmailSystem
        )
        print("✅ All subsystems imported successfully")
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        requirements_met = False
    
    # Check that CampusTask can be imported
    try:
        from tasks.instance.campus_life_bench.task import CampusTask
        print("✅ CampusTask imported successfully")
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        requirements_met = False
    
    # Check that CampusEnvironment can be imported
    try:
        from tasks.instance.campus_life_bench.environment import CampusEnvironment
        print("✅ CampusEnvironment imported successfully")
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        requirements_met = False
    
    return requirements_met


def run_smoke_test():
    """Run a basic smoke test to ensure everything works"""
    print("=" * 60)
    print("RUNNING SMOKE TEST")
    print("=" * 60)
    
    try:
        # Import and create basic instances
        from tasks.instance.campus_life_bench.task import CampusTask
        from tasks.instance.campus_life_bench.environment import CampusEnvironment
        from factories.chat_history_item import ChatHistoryItemFactory
        
        # Create instances
        chat_factory = ChatHistoryItemFactory()
        task = CampusTask(chat_factory, max_round=5)
        
        print("✅ CampusTask created successfully")
        
        # Test basic environment functionality
        result = task.campus_environment.send_email(
            "test@university.edu",
            "Test Subject",
            "Test body"
        )
        
        if result.is_success():
            print("✅ Email system working")
        else:
            print(f"❌ Email system failed: {result.message}")
            return False
        
        # Test calendar system
        result = task.campus_environment.add_event(
            "self",
            "Test Event",
            "Test Location",
            "Week 1, Monday, 10:00-11:00"
        )
        
        if result.is_success():
            print("✅ Calendar system working")
        else:
            print(f"❌ Calendar system failed: {result.message}")
            return False
        
        # Test map system
        result = task.campus_environment.find_building_id("Lakeside Dormitory")
        
        if result.is_success():
            print("✅ Map system working")
        else:
            print(f"❌ Map system failed: {result.message}")
            return False
        
        print("✅ Smoke test passed")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="CampusLifeBench Test Runner")
    parser.add_argument("--test", help="Run specific test module")
    parser.add_argument("--smoke", action="store_true", help="Run smoke test only")
    parser.add_argument("--validate", action="store_true", help="Validate requirements only")
    parser.add_argument("--all", action="store_true", help="Run all tests and validations")
    
    args = parser.parse_args()
    
    success = True
    
    if args.validate or args.all:
        if not validate_requirements():
            success = False
            print("\n❌ Requirements validation failed")
        else:
            print("\n✅ Requirements validation passed")
    
    if args.smoke or args.all:
        if not run_smoke_test():
            success = False
            print("\n❌ Smoke test failed")
        else:
            print("\n✅ Smoke test passed")
    
    if args.test:
        if not run_specific_test(args.test):
            success = False
            print(f"\n❌ Test {args.test} failed")
        else:
            print(f"\n✅ Test {args.test} passed")
    
    elif not args.smoke and not args.validate and not args.test:
        # Run all unit tests by default
        if not run_unit_tests():
            success = False
            print("\n❌ Unit tests failed")
        else:
            print("\n✅ Unit tests passed")
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("CampusLifeBench implementation is ready for use.")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ SOME TESTS FAILED!")
        print("Please fix the issues before using CampusLifeBench.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
