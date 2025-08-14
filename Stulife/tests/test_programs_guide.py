#!/usr/bin/env python3
"""
Test script to verify Academic Programs Guide integration
"""

import sys
import json
from pathlib import Path

# Add the LifelongAgentBench source to Python path
sys.path.insert(0, str(Path(__file__).parent / "LifelongAgentBench-main" / "src"))

try:
    from tasks.instance.campus_life_bench.environment import CampusEnvironment
    
    def test_programs_guide():
        """Test Academic Programs Guide functionality"""
        print("🧪 Testing Academic Programs Guide integration...")
        
        # Test with background directory
        background_data_dir = Path("任务数据")
        
        try:
            # Initialize CampusEnvironment with background data
            env = CampusEnvironment(data_dir=str(background_data_dir))
            print("✅ CampusEnvironment initialized successfully")
            
            # Test listing chapters for Academic Programs Guide
            print("\n📚 Testing Academic Programs Guide access...")
            result = env.list_chapters("Academic Programs Guide")
            if result.is_success():
                chapters = result.data.get('chapters', [])
                print(f"✅ Found {len(chapters)} chapters in Academic Programs Guide")
                
                # Show chapter titles
                for i, chapter in enumerate(chapters[:3]):  # Show first 3
                    print(f"  Chapter {i+1}: {chapter}")
                if len(chapters) > 3:
                    print(f"  ... and {len(chapters) - 3} more chapters")
            else:
                print(f"❌ Failed to access Academic Programs Guide: {result.message}")
                return False
            
            # Test accessing a specific section
            print("\n📖 Testing section access...")
            if chapters:
                first_chapter = chapters[0]
                result = env.list_sections("Academic Programs Guide", first_chapter)
                if result.is_success():
                    sections = result.data.get('sections', [])
                    print(f"✅ Found {len(sections)} sections in first chapter")
                    
                    # Show section titles
                    for i, section in enumerate(sections[:2]):  # Show first 2
                        print(f"  Section {i+1}: {section}")
                else:
                    print(f"❌ Failed to access sections: {result.message}")
            
            # Test accessing articles
            print("\n📄 Testing article access...")
            if chapters:
                first_chapter = chapters[0]
                result = env.list_sections("Academic Programs Guide", first_chapter)
                if result.is_success():
                    sections = result.data.get('sections', [])
                    if sections:
                        first_section = sections[0]
                        result = env.list_articles("Academic Programs Guide", first_chapter, first_section)
                        if result.is_success():
                            articles = result.data.get('articles', [])
                            print(f"✅ Found {len(articles)} articles in first section")
                            
                            # Test viewing an article
                            if articles:
                                first_article = articles[0]
                                result = env.view_article(first_article['title'], 'title')
                                if result.is_success():
                                    content = result.data.get('body', '')
                                    print(f"✅ Successfully viewed article: {first_article['title']}")
                                    print(f"  Content length: {len(content)} characters")
                                    print(f"  Preview: {content[:100]}...")
                                else:
                                    print(f"❌ Failed to view article: {result.message}")
                        else:
                            print(f"❌ Failed to access articles: {result.message}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_bibliography_statistics():
        """Test bibliography statistics"""
        print("\n📊 Testing bibliography statistics...")
        
        try:
            # Load bibliography data directly
            bibliography_file = Path("任务数据/background/bibliography.json")
            with open(bibliography_file, 'r', encoding='utf-8') as f:
                bibliography_data = json.load(f)
            
            books = bibliography_data.get('books', [])
            handbooks = [book for book in books if book.get('book_type') == 'handbook']
            textbooks = [book for book in books if book.get('book_type') == 'textbook']
            
            print(f"✅ Total books: {len(books)}")
            print(f"✅ Handbooks: {len(handbooks)}")
            print(f"✅ Textbooks: {len(textbooks)}")
            
            print("\n📚 Handbook titles:")
            for handbook in handbooks:
                title = handbook.get('book_title', 'Unknown')
                chapters = handbook.get('chapters', [])
                print(f"  - {title} ({len(chapters)} chapters)")
            
            # Check Academic Programs Guide specifically
            programs_guide = None
            for book in books:
                if book.get('book_title') == 'Academic Programs Guide':
                    programs_guide = book
                    break
            
            if programs_guide:
                chapters = programs_guide.get('chapters', [])
                print(f"\n🎯 Academic Programs Guide details:")
                print(f"  - Chapters: {len(chapters)}")
                
                total_sections = sum(len(chapter.get('sections', [])) for chapter in chapters)
                total_articles = sum(
                    len(section.get('articles', []))
                    for chapter in chapters
                    for section in chapter.get('sections', [])
                )
                
                print(f"  - Total sections: {total_sections}")
                print(f"  - Total articles: {total_articles}")
                
                # Show chapter titles
                print("  - Chapter titles:")
                for chapter in chapters:
                    title = chapter.get('chapter_title', 'Unknown')
                    print(f"    • {title}")
            else:
                print("❌ Academic Programs Guide not found!")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error during statistics testing: {e}")
            return False
    
    if __name__ == "__main__":
        print("🚀 Starting Academic Programs Guide tests...\n")
        
        # Test programs guide functionality
        guide_success = test_programs_guide()
        
        # Test statistics
        stats_success = test_bibliography_statistics()
        
        if guide_success and stats_success:
            print("\n🎉 All Academic Programs Guide tests passed!")
        else:
            print("\n❌ Some Academic Programs Guide tests failed.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the LifelongAgentBench source code is available and properly structured.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
