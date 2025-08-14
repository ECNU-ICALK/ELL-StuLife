#!/usr/bin/env python3
"""
Test script to verify course data loading functionality
"""

import sys
import os
from pathlib import Path

# Add the LifelongAgentBench source to Python path
sys.path.insert(0, str(Path(__file__).parent / "LifelongAgentBench-main" / "src"))

try:
    from tasks.instance.campus_life_bench.environment import CampusEnvironment
    
    def test_course_data_loading():
        """Test loading course data from the new structure"""
        print("🧪 Testing course data loading...")
        
        # Test with background directory
        background_data_dir = Path("任务数据")
        
        try:
            # Initialize CampusEnvironment with background data
            env = CampusEnvironment(data_dir=str(background_data_dir))
            print("✅ CampusEnvironment initialized successfully")
            
            # Test course browsing
            print("\n📚 Testing course browsing...")
            result = env.browse_courses()
            if result.is_success():
                courses = result.data.get('courses', [])
                print(f"✅ Course browsing test passed: Found {len(courses)} courses")
                
                # Show some course details
                if courses:
                    sample_course = courses[0]
                    print(f"  Sample course: {sample_course.get('course_name')} ({sample_course.get('course_code')})")
                    print(f"  Instructor: {sample_course.get('instructor', {}).get('name')}")
                    print(f"  Credits: {sample_course.get('credits')}")
                    print(f"  Semester: {sample_course.get('semester')}")
            else:
                print(f"❌ Course browsing test failed: {result.message}")
            
            # Test course filtering
            print("\n🔍 Testing course filtering...")
            result = env.browse_courses(filters={"type": "Compulsory"})
            if result.is_success():
                compulsory_courses = result.data.get('courses', [])
                print(f"✅ Course filtering test passed: Found {len(compulsory_courses)} compulsory courses")
            else:
                print(f"❌ Course filtering test failed: {result.message}")
            
            # Test course filtering by credits
            print("\n📊 Testing course filtering by credits...")
            result = env.browse_courses(filters={"credits": 3})
            if result.is_success():
                three_credit_courses = result.data.get('courses', [])
                print(f"✅ Credit filtering test passed: Found {len(three_credit_courses)} courses with 3 credits")
            else:
                print(f"❌ Credit filtering test failed: {result.message}")
            
            print("\n🎉 All course tests completed!")
            return True
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_course_statistics():
        """Test course data statistics"""
        print("\n📊 Testing course statistics...")
        
        try:
            import json
            
            # Load course data directly
            courses_file = Path("任务数据/background/courses.json")
            with open(courses_file, 'r', encoding='utf-8') as f:
                courses_data = json.load(f)
            
            courses = courses_data.get('courses', [])
            metadata = courses_data.get('metadata', {})
            
            print(f"✅ Total courses: {len(courses)}")
            print(f"✅ Metadata total: {metadata.get('total_courses')}")
            print(f"✅ Semester 1 courses: {metadata.get('semester_1_courses')}")
            print(f"✅ Semester 2 courses: {metadata.get('semester_2_courses')}")
            
            # Count by type
            type_counts = {}
            for course in courses:
                course_type = course.get('type', 'Unknown')
                type_counts[course_type] = type_counts.get(course_type, 0) + 1
            
            print("✅ Course types:")
            for course_type, count in type_counts.items():
                print(f"    - {course_type}: {count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during statistics testing: {e}")
            return False
    
    if __name__ == "__main__":
        print("🚀 Starting course data loading tests...\n")
        
        # Test course loading
        loading_success = test_course_data_loading()
        
        # Test statistics
        stats_success = test_course_statistics()
        
        if loading_success and stats_success:
            print("\n🎉 All course tests passed! Course data loading is working correctly.")
        else:
            print("\n❌ Some course tests failed. Please check the implementation.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the LifelongAgentBench source code is available and properly structured.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
