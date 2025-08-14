#!/usr/bin/env python3
"""
Simple test script for CampusLifeBench
Tests basic functionality and imports
"""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all components can be imported"""
    print("Testing imports...")
    
    try:
        from tasks.instance.campus_life_bench.systems.email import EmailSystem
        print("✅ EmailSystem imported")
        
        from tasks.instance.campus_life_bench.systems.world_and_calendar import CalendarSystem, WorldTimeSystem
        print("✅ Calendar systems imported")
        
        from tasks.instance.campus_life_bench.systems.map_and_geography import MapLookupSystem, GeographySystem
        print("✅ Map systems imported")
        
        from tasks.instance.campus_life_bench.systems.reservation import ReservationSystem
        print("✅ ReservationSystem imported")
        
        from tasks.instance.campus_life_bench.systems.information import InformationSystem
        print("✅ InformationSystem imported")
        
        from tasks.instance.campus_life_bench.systems.course_selection import CourseSelectionSystem
        print("✅ CourseSelectionSystem imported")
        
        from tasks.instance.campus_life_bench.tools import ToolResult, ToolManager
        print("✅ Tools imported")
        
        from tasks.instance.campus_life_bench.environment import CampusEnvironment
        print("✅ CampusEnvironment imported")
        
        from tasks.instance.campus_life_bench.task import CampusTask
        print("✅ CampusTask imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality"""
    print("\nTesting basic functionality...")
    
    try:
        from tasks.instance.campus_life_bench.systems.email import EmailSystem
        
        # Test email system
        email_system = EmailSystem()
        result = email_system.send_email(
            "test@university.edu",
            "Test Subject",
            "Test body content"
        )
        
        if result.is_success():
            print("✅ Email system working")
        else:
            print(f"❌ Email system failed: {result.message}")
            return False
        
        # Test calendar system
        from tasks.instance.campus_life_bench.systems.world_and_calendar import CalendarSystem
        
        calendar_system = CalendarSystem()
        result = calendar_system.add_event(
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
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_environment():
    """Test CampusEnvironment"""
    print("\nTesting CampusEnvironment...")
    
    try:
        from tasks.instance.campus_life_bench.environment import CampusEnvironment
        
        # Create environment with temporary data directory
        data_dir = Path(__file__).parent / "src" / "tasks" / "instance" / "campus_life_bench" / "data"
        env = CampusEnvironment(data_dir)
        
        # Test email sending
        result = env.send_email(
            "test@university.edu",
            "Test Subject",
            "Test body"
        )
        
        if result.is_success():
            print("✅ Environment email working")
        else:
            print(f"❌ Environment email failed: {result.message}")
            return False
        
        # Test calendar
        result = env.add_event(
            "self",
            "Test Event",
            "Test Location",
            "Week 1, Monday, 14:00-15:00"
        )
        
        if result.is_success():
            print("✅ Environment calendar working")
        else:
            print(f"❌ Environment calendar failed: {result.message}")
            return False
        
        # Test map lookup
        result = env.find_building_id("Lakeside Dormitory")
        
        if result.is_success():
            print("✅ Environment map working")
        else:
            print(f"❌ Environment map failed: {result.message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("CampusLifeBench Basic Test Suite")
    print("=" * 60)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    # Test environment
    if not test_environment():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("CampusLifeBench is working correctly.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the implementation.")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
