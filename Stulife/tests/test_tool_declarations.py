#!/usr/bin/env python3
"""
Test script to verify tool declarations match the actual background data
"""

import sys
import json
from pathlib import Path

# Add the LifelongAgentBench source to Python path
sys.path.insert(0, str(Path(__file__).parent / "LifelongAgentBench-main" / "src"))

try:
    from tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator
    
    def test_tool_declarations():
        """Test that tool declarations match actual data"""
        print("🧪 Testing tool declarations against actual data...")
        
        # Load actual background data
        background_dir = Path("任务数据/background")
        
        # Load bibliography data
        bibliography_file = background_dir / "bibliography.json"
        with open(bibliography_file, 'r', encoding='utf-8') as f:
            bibliography_data = json.load(f)
        
        books = bibliography_data.get('books', [])
        handbooks = [book for book in books if book.get('book_type') == 'handbook']
        textbooks = [book for book in books if book.get('book_type') == 'textbook']
        
        print(f"📚 Found {len(books)} total books:")
        print(f"  - {len(handbooks)} handbooks")
        print(f"  - {len(textbooks)} textbooks")
        
        # Load course data
        courses_file = background_dir / "courses.json"
        with open(courses_file, 'r', encoding='utf-8') as f:
            courses_data = json.load(f)
        
        total_courses = courses_data.get('metadata', {}).get('total_courses', 0)
        print(f"📖 Found {total_courses} total courses")
        
        # Load campus data
        campus_file = background_dir / "campus_data.json"
        with open(campus_file, 'r', encoding='utf-8') as f:
            campus_data = json.load(f)
        
        clubs = campus_data.get('clubs', [])
        advisors = campus_data.get('advisors', [])
        library_books = campus_data.get('library_books', [])
        
        print(f"🏫 Found campus data:")
        print(f"  - {len(clubs)} clubs")
        print(f"  - {len(advisors)} advisors")
        print(f"  - {len(library_books)} library books")
        
        return {
            'handbooks': [book['book_title'] for book in handbooks],
            'textbooks': [book['book_title'] for book in textbooks],
            'total_courses': total_courses,
            'total_clubs': len(clubs),
            'total_advisors': len(advisors),
            'total_library_books': len(library_books)
        }
    
    def test_prompt_generation():
        """Test system prompt generation with tool declarations"""
        print("\n🎯 Testing system prompt generation...")
        
        try:
            generator = SystemPromptGenerator()
            
            # Test generating prompt with bibliography and data_system
            prompt = generator.generate_prompt(['bibliography', 'data_system', 'course_selection'])
            
            # Check if the prompt contains the expected information
            checks = [
                ('Student Handbook' in prompt, "Student Handbook mentioned"),
                ('Academic Integrity Guidelines' in prompt, "Academic Integrity Guidelines mentioned"),
                ('Academic Programs Guide' in prompt, "Academic Programs Guide mentioned"),
                ('A Panorama of Computing' in prompt, "Computer Science textbook mentioned"),
                ('226 total courses' in prompt, "Course count mentioned"),
                ('Student Clubs (101 total)' in prompt, "Club count mentioned"),
                ('Faculty Advisors (1000 total)' in prompt, "Advisor count mentioned")
            ]
            
            print("✅ Prompt generation successful")
            print("🔍 Checking prompt content:")
            
            for check_passed, description in checks:
                status = "✅" if check_passed else "❌"
                print(f"  {status} {description}")
            
            # Count successful checks
            passed_checks = sum(1 for check, _ in checks if check)
            total_checks = len(checks)
            
            print(f"\n📊 Prompt validation: {passed_checks}/{total_checks} checks passed")
            
            return passed_checks == total_checks
            
        except Exception as e:
            print(f"❌ Error during prompt generation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_specific_tool_descriptions():
        """Test specific tool descriptions"""
        print("\n🔧 Testing specific tool descriptions...")
        
        try:
            generator = SystemPromptGenerator()
            tool_descriptions = generator.tool_descriptions
            
            # Test bibliography tool
            bib_desc = tool_descriptions.get('bibliography.list_chapters', '')
            print("📚 Bibliography tool description:")
            if 'Student Handbook' in bib_desc and 'A Panorama of Computing' in bib_desc:
                print("  ✅ Contains correct book titles")
            else:
                print("  ❌ Missing expected book titles")
            
            # Test data system tool
            data_desc = tool_descriptions.get('data_system.list_by_category', '')
            print("🏫 Data system tool description:")
            if 'Student Clubs (101 total)' in data_desc and 'Faculty Advisors (1000 total)' in data_desc:
                print("  ✅ Contains correct counts")
            else:
                print("  ❌ Missing expected counts")
            
            # Test course selection tool
            course_desc = tool_descriptions.get('course_selection.browse_courses', '')
            print("📖 Course selection tool description:")
            if '226 total courses' in course_desc:
                print("  ✅ Contains correct course count")
            else:
                print("  ❌ Missing expected course count")
            
            # Test student handbook tool
            handbook_desc = tool_descriptions.get('student_handbook.list_available', '')
            print("📋 Student handbook tool description:")
            if 'Student Handbook' in handbook_desc and 'Academic Integrity Guidelines' in handbook_desc and 'Academic Programs Guide' in handbook_desc:
                print("  ✅ Contains correct handbook titles")
            else:
                print("  ❌ Missing expected handbook titles")
            
            # Test textbooks tool
            textbook_desc = tool_descriptions.get('textbooks.list_available', '')
            print("📚 Textbooks tool description:")
            if 'A Panorama of Computing' in textbook_desc and 'Linear Algebra' in textbook_desc:
                print("  ✅ Contains correct textbook titles")
            else:
                print("  ❌ Missing expected textbook titles")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during tool description testing: {e}")
            return False
    
    if __name__ == "__main__":
        print("🚀 Starting tool declaration tests...\n")
        
        # Test data loading
        data_stats = test_tool_declarations()
        
        # Test prompt generation
        prompt_success = test_prompt_generation()
        
        # Test specific tool descriptions
        tool_success = test_specific_tool_descriptions()
        
        print(f"\n📊 Summary:")
        print(f"  - Background data: ✅ Loaded successfully")
        print(f"  - Prompt generation: {'✅' if prompt_success else '❌'} {'Passed' if prompt_success else 'Failed'}")
        print(f"  - Tool descriptions: {'✅' if tool_success else '❌'} {'Passed' if tool_success else 'Failed'}")
        
        if prompt_success and tool_success:
            print("\n🎉 All tool declaration tests passed!")
        else:
            print("\n❌ Some tool declaration tests failed.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the LifelongAgentBench source code is available and properly structured.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
