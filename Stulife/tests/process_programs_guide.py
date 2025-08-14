#!/usr/bin/env python3
"""
Script to process informatics division programs and convert to chapter-section-article format
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load JSON file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def convert_content_to_text(content_items: List[Dict[str, Any]]) -> str:
    """Convert content items to formatted text"""
    text_parts = []
    
    for item in content_items:
        item_type = item.get('type', '')
        
        if item_type == 'heading':
            level = item.get('level', 1)
            text = item.get('text', '')
            # Add heading with appropriate formatting
            text_parts.append(f"{'#' * level} {text}")
            
        elif item_type == 'paragraph':
            text = item.get('text', '')
            text_parts.append(text)
            
        elif item_type == 'list':
            items = item.get('items', [])
            for list_item in items:
                text_parts.append(f"• {list_item}")
                
        elif item_type == 'table':
            # Handle table data
            data = item.get('data', [])
            parsing_mode = item.get('parsing_mode', '')
            
            if parsing_mode == 'graduation_requirements':
                for req_item in data:
                    requirement = req_item.get('requirement', '')
                    indicators = req_item.get('indicators', [])
                    
                    text_parts.append(f"**{requirement}**")
                    for indicator in indicators:
                        text_parts.append(f"  - {indicator}")
            else:
                # Handle other table formats
                text_parts.append("Table data:")
                for row in data:
                    if isinstance(row, dict):
                        for key, value in row.items():
                            text_parts.append(f"  {key}: {value}")
    
    return '\n\n'.join(text_parts)

def process_programs_guide():
    """Process the informatics division programs guide"""
    print("🔄 Processing Academic Programs Guide...")
    
    # Load the programs file
    programs_file = Path("任务数据/background/books/informatics_division_programs_anonymized.json")
    programs_data = load_json_file(programs_file)
    
    if not programs_data:
        print("❌ Failed to load programs data")
        return None
    
    # Extract basic information
    document_title = programs_data.get('documentSet', 'Academic Programs Guide')
    programs = programs_data.get('programs', [])
    
    print(f"📚 Processing document: {document_title}")
    print(f"📖 Found {len(programs)} programs")
    
    # Create chapters for each program
    chapters = []
    
    for i, program in enumerate(programs):
        program_code = program.get('program_code', f'P{i+1}')
        major = program.get('major', f'Program {i+1}')
        school = program.get('school', 'Unknown Department')
        content = program.get('content', [])
        
        print(f"  Processing: {major} ({program_code})")
        
        # Create chapter
        chapter = {
            "chapter_title": f"Chapter {i+1}: {major}",
            "sections": []
        }
        
        # Group content into sections based on headings
        current_section = None
        current_articles = []
        article_counter = 1
        
        for content_item in content:
            item_type = content_item.get('type', '')
            
            if item_type == 'heading' and content_item.get('level') == 3:
                # This is a section heading
                if current_section:
                    # Save previous section
                    current_section['articles'] = current_articles
                    chapter['sections'].append(current_section)
                
                # Start new section
                section_title = content_item.get('text', f'Section {len(chapter["sections"]) + 1}')
                current_section = {
                    "section_title": f"{len(chapter['sections']) + 1}. {section_title}",
                    "articles": []
                }
                current_articles = []
                article_counter = 1
                
            elif current_section:
                # Add content to current article
                if not current_articles or len(current_articles[-1]['body']) > 2000:
                    # Start new article if none exists or current one is too long
                    article_id = f"prog_{program_code}_{len(chapter['sections'])}_{article_counter}"
                    article_title = f"Article {article_counter}"
                    
                    # Try to get a meaningful title from heading
                    if item_type == 'heading':
                        article_title = content_item.get('text', article_title)
                    
                    current_articles.append({
                        "article_id": article_id,
                        "title": article_title,
                        "body": ""
                    })
                    article_counter += 1
                
                # Convert content item to text and add to current article
                if current_articles:
                    item_text = convert_content_to_text([content_item])
                    if current_articles[-1]['body']:
                        current_articles[-1]['body'] += '\n\n' + item_text
                    else:
                        current_articles[-1]['body'] = item_text
        
        # Don't forget the last section
        if current_section:
            current_section['articles'] = current_articles
            chapter['sections'].append(current_section)
        
        # If no sections were created, create a default one
        if not chapter['sections']:
            all_content_text = convert_content_to_text(content)
            chapter['sections'] = [{
                "section_title": "1. Program Overview",
                "articles": [{
                    "article_id": f"prog_{program_code}_1_1",
                    "title": "Program Details",
                    "body": all_content_text
                }]
            }]
        
        chapters.append(chapter)
    
    # Create the book structure
    programs_book = {
        "book_title": "Academic Programs Guide",
        "book_type": "handbook",
        "version": "1.0",
        "last_updated": "2024-01-01",
        "chapters": chapters
    }
    
    print(f"✅ Created book with {len(chapters)} chapters")
    
    return programs_book

def update_bibliography():
    """Update bibliography.json to include the programs guide"""
    print("\n📚 Updating bibliography.json...")
    
    # Process the programs guide
    programs_book = process_programs_guide()
    if not programs_book:
        print("❌ Failed to process programs guide")
        return False
    
    # Load existing bibliography
    bibliography_file = Path("任务数据/background/bibliography.json")
    bibliography_data = load_json_file(bibliography_file)
    
    if not bibliography_data:
        print("❌ Failed to load existing bibliography")
        return False
    
    books = bibliography_data.get('books', [])
    
    # Check if Academic Programs Guide already exists
    existing_guide = None
    for i, book in enumerate(books):
        if book.get('book_title') == 'Academic Programs Guide':
            existing_guide = i
            break
    
    if existing_guide is not None:
        # Replace existing guide
        books[existing_guide] = programs_book
        print("✅ Replaced existing Academic Programs Guide")
    else:
        # Add new guide
        books.append(programs_book)
        print("✅ Added new Academic Programs Guide")
    
    # Update bibliography data
    bibliography_data['books'] = books
    
    # Save updated bibliography
    with open(bibliography_file, 'w', encoding='utf-8') as f:
        json.dump(bibliography_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Updated bibliography.json with {len(books)} books")
    
    # Print statistics
    handbooks = [book for book in books if book.get('book_type') == 'handbook']
    textbooks = [book for book in books if book.get('book_type') == 'textbook']
    
    print(f"📊 Bibliography statistics:")
    print(f"  - Total books: {len(books)}")
    print(f"  - Handbooks: {len(handbooks)}")
    print(f"  - Textbooks: {len(textbooks)}")
    
    return True

def main():
    """Main processing function"""
    print("🚀 Starting Academic Programs Guide processing...")
    
    success = update_bibliography()
    
    if success:
        print("\n🎉 Academic Programs Guide processing completed successfully!")
    else:
        print("\n❌ Academic Programs Guide processing failed!")

if __name__ == "__main__":
    main()
