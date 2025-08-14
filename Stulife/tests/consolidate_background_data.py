#!/usr/bin/env python3
"""
Script to consolidate background data files into standardized format
"""

import json
import os
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

def normalize_book_structure(book_data: Dict[str, Any], book_title: str, book_type: str = "textbook") -> Dict[str, Any]:
    """Normalize book data to standard structure"""
    
    # Handle different input formats
    if isinstance(book_data, list):
        # Handle array format (like university_rules.json)
        if book_data and isinstance(book_data[0], dict):
            book_info = book_data[0]
            content = book_info.get("content", [])
        else:
            return {}
    else:
        # Handle object format
        content = book_data.get("content", [])
        book_info = book_data
    
    # Extract chapters
    chapters = []
    for chapter_data in content:
        if chapter_data.get("type") == "chapter":
            chapter = {
                "chapter_title": chapter_data.get("title", ""),
                "sections": []
            }
            
            # Extract sections
            for section_data in chapter_data.get("content", []):
                if section_data.get("type") == "section":
                    section = {
                        "section_title": section_data.get("title", ""),
                        "articles": []
                    }
                    
                    # Extract articles
                    for article_data in section_data.get("content", []):
                        if article_data.get("type") == "article":
                            article = {
                                "article_id": article_data.get("id", ""),
                                "title": article_data.get("title", ""),
                                "body": article_data.get("content", "")
                            }
                            section["articles"].append(article)
                    
                    chapter["sections"].append(section)
            
            chapters.append(chapter)
    
    return {
        "book_title": book_title,
        "book_type": book_type,
        "version": book_info.get("version", "1.0"),
        "last_updated": book_info.get("last_updated", "2024-01-01"),
        "chapters": chapters
    }

def consolidate_books():
    """Consolidate all book files into bibliography.json"""
    books_dir = Path("任务数据/background/books")
    output_dir = Path("任务数据/background")
    
    consolidated_books = {"books": []}
    
    # Define book mappings
    book_mappings = {
        "university_rules.json": ("Student Handbook", "handbook"),
        "academic_integrity.json": ("Academic Integrity Guidelines", "handbook"),
        "informatics_division_programs_anonymized.json": ("Academic Programs Guide", "handbook"),
        "IntroductionCS.json": ("A Panorama of Computing: From Bits to Artificial Intelligence", "textbook"),
        "Linear Algebra.json": ("Linear Algebra and Its Applications", "textbook"),
        "Mathematical Analysis.json": ("Mathematical Analysis", "textbook"),
        "Military Theory.json": ("Military Theory and National Defense", "textbook"),
        "Programming4Everyone.json": ("Programming for Everyone", "textbook"),
        "innovation.json": ("Innovation and Entrepreneurship", "textbook"),
        "mental.json": ("Mental Health and Wellness", "textbook"),
        "programing.json": ("Advanced Programming Concepts", "textbook")
    }
    
    for filename, (book_title, book_type) in book_mappings.items():
        file_path = books_dir / filename
        if file_path.exists():
            print(f"Processing {filename}...")
            book_data = load_json_file(file_path)
            if book_data:
                normalized_book = normalize_book_structure(book_data, book_title, book_type)
                if normalized_book.get("chapters"):
                    consolidated_books["books"].append(normalized_book)
                    print(f"  ✅ Added {book_title}")
                else:
                    print(f"  ⚠️  No content found in {filename}")
        else:
            print(f"  ❌ File not found: {filename}")
    
    # Save consolidated bibliography
    output_path = output_dir / "bibliography.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated_books, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Consolidated {len(consolidated_books['books'])} books into {output_path}")
    return consolidated_books

def consolidate_campus_data():
    """Consolidate campus information files into campus_data.json"""
    info_dir = Path("任务数据/background/info")
    output_dir = Path("任务数据/background")
    
    campus_data = {
        "clubs": [],
        "advisors": [],
        "library_seats": {"buildings": []},
        "library_books": []
    }
    
    # Load advisors
    advisor_file = info_dir / "advisor.json"
    if advisor_file.exists():
        advisors = load_json_file(advisor_file)
        if isinstance(advisors, list):
            campus_data["advisors"] = advisors
            print(f"✅ Loaded {len(advisors)} advisors")
    
    # Load student clubs
    clubs_file = info_dir / "student_clubs.json"
    if clubs_file.exists():
        clubs_data = load_json_file(clubs_file)
        if isinstance(clubs_data, list):
            campus_data["clubs"] = clubs_data
            print(f"✅ Loaded {len(clubs_data)} clubs")
        elif isinstance(clubs_data, dict) and "clubs" in clubs_data:
            campus_data["clubs"] = clubs_data["clubs"]
            print(f"✅ Loaded {len(clubs_data['clubs'])} clubs")
    
    # Load library seats
    lib_seats_file = info_dir / "lib_map_with_seats.json"
    if lib_seats_file.exists():
        lib_seats = load_json_file(lib_seats_file)
        if lib_seats:
            campus_data["library_seats"] = lib_seats
            print("✅ Loaded library seat map")
    
    # Load library books database
    lib_books_file = info_dir / "lib_books_database.json"
    if lib_books_file.exists():
        lib_books = load_json_file(lib_books_file)
        if isinstance(lib_books, list):
            campus_data["library_books"] = lib_books
            print(f"✅ Loaded {len(lib_books)} library books")
        elif isinstance(lib_books, dict) and "books" in lib_books:
            campus_data["library_books"] = lib_books["books"]
            print(f"✅ Loaded {len(lib_books['books'])} library books")
    
    # Save consolidated campus data
    output_path = output_dir / "campus_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(campus_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Consolidated campus data into {output_path}")
    return campus_data

def copy_existing_files():
    """Copy existing files that don't need consolidation"""
    info_dir = Path("任务数据/background/info")
    output_dir = Path("任务数据/background")
    
    files_to_copy = ["map_v1.5.json"]
    
    for filename in files_to_copy:
        src_path = info_dir / filename
        dst_path = output_dir / filename
        
        if src_path.exists():
            import shutil
            shutil.copy2(src_path, dst_path)
            print(f"✅ Copied {filename}")
        else:
            print(f"❌ File not found: {filename}")

def main():
    """Main consolidation process"""
    print("🚀 Starting background data consolidation...")
    
    # Create output directory if it doesn't exist
    output_dir = Path("任务数据/background")
    output_dir.mkdir(exist_ok=True)
    
    # Consolidate books
    print("\n📚 Consolidating books...")
    consolidate_books()
    
    # Consolidate campus data
    print("\n🏫 Consolidating campus data...")
    consolidate_campus_data()
    
    # Copy existing files
    print("\n📋 Copying existing files...")
    copy_existing_files()
    
    print("\n🎉 Background data consolidation completed!")

if __name__ == "__main__":
    main()
