"""
Bibliography and Information Query System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..tools import ToolResult, ensure_english_message


class InformationSystem:
    """
    Static information query system for bibliography and campus data
    Provides read-only access to structured book and campus information
    """
    
    def __init__(self, bibliography_path: Path, data_system_path: Path):
        """
        Initialize information system
        
        Args:
            bibliography_path: Path to bibliography JSON file
            data_system_path: Path to campus data JSON file
        """
        self.bibliography_path = bibliography_path
        self.data_system_path = data_system_path
        
        self._bibliography_data: Optional[Dict[str, Any]] = None
        self._data_system_data: Optional[Dict[str, Any]] = None
        
        self._load_data()
    
    def _load_data(self):
        """Load bibliography and data system data from JSON files"""
        # Load bibliography data
        try:
            with open(self.bibliography_path, 'r', encoding='utf-8') as f:
                self._bibliography_data = json.load(f)
        except FileNotFoundError:
            # Create minimal bibliography data if file doesn't exist
            self._bibliography_data = {
                "books": [
                    {
                        "book_title": "Introduction to Computer Science",
                        "chapters": [
                            {
                                "chapter_title": "Chapter 1: Fundamentals",
                                "sections": [
                                    {
                                        "section_title": "Section 1.1: Basic Concepts",
                                        "articles": [
                                            {
                                                "article_id": "cs_intro_001",
                                                "title": "What is Computer Science?",
                                                "body": "Computer science is the study of computational systems and the design of computer systems and their applications."
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        
        # Load data system data
        try:
            with open(self.data_system_path, 'r', encoding='utf-8') as f:
                self._data_system_data = json.load(f)
        except FileNotFoundError:
            # Create minimal data system data if file doesn't exist
            self._data_system_data = {
                "clubs": [
                    {
                        "club_id": "C001",
                        "club_name": "Computer Science Club",
                        "category": "Academic",
                        "description": "A club for computer science enthusiasts",
                        "recruitment_info": "Open to all students interested in computer science"
                    }
                ],
                "advisors": [
                    {
                        "advisor_id": "T001",
                        "name": "Dr. John Smith",
                        "gender": "Male",
                        "age": 45,
                        "email": "john.smith@university.edu",
                        "research_area": {
                            "level_1": "Computer Science",
                            "level_2": "Artificial Intelligence",
                            "tags": ["Machine Learning", "Natural Language Processing"]
                        },
                        "representative_work": ["AI in Education", "NLP Applications"],
                        "preferences": {"meeting_time": "afternoon", "communication": "email"}
                    }
                ]
            }
    
    # ========== Bibliography Query Tools ==========
    
    def list_chapters(self, book_title: str) -> ToolResult:
        """
        List all chapters in the specified book
        
        Args:
            book_title: Title of the book
            
        Returns:
            ToolResult with chapter list
        """
        try:
            if not book_title:
                return ToolResult.failure("Book title is required.")
            
            # Find the book
            for book in self._bibliography_data["books"]:
                if book["book_title"].lower() == book_title.lower():
                    chapters = [chapter["chapter_title"] for chapter in book["chapters"]]
                    
                    if chapters:
                        message = f"Book '{book_title}' contains the following chapters: {', '.join(chapters)}."
                    else:
                        message = f"Book '{book_title}' has no chapters."
                    
                    return ToolResult.success(ensure_english_message(message), {
                        "book_title": book["book_title"],
                        "chapters": chapters
                    })
            
            return ToolResult.failure(f"Book '{book_title}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to list chapters: {str(e)}")
    
    def list_sections(self, book_title: str, chapter_title: str) -> ToolResult:
        """
        List all sections in the specified chapter
        
        Args:
            book_title: Title of the book
            chapter_title: Title of the chapter
            
        Returns:
            ToolResult with section list
        """
        try:
            if not all([book_title, chapter_title]):
                return ToolResult.failure("Both book title and chapter title are required.")
            
            # Find the book and chapter
            for book in self._bibliography_data["books"]:
                if book["book_title"].lower() == book_title.lower():
                    for chapter in book["chapters"]:
                        if chapter["chapter_title"].lower() == chapter_title.lower():
                            sections = [section["section_title"] for section in chapter["sections"]]
                            
                            if sections:
                                message = f"Chapter '{chapter_title}' in book '{book_title}' contains the following sections: {', '.join(sections)}."
                            else:
                                message = f"Chapter '{chapter_title}' in book '{book_title}' has no sections."
                            
                            return ToolResult.success(ensure_english_message(message), {
                                "book_title": book["book_title"],
                                "chapter_title": chapter["chapter_title"],
                                "sections": sections
                            })
                    
                    return ToolResult.failure(f"Chapter '{chapter_title}' not found in book '{book_title}'.")
            
            return ToolResult.failure(f"Book '{book_title}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to list sections: {str(e)}")
    
    def list_articles(self, book_title: str, chapter_title: str, section_title: str) -> ToolResult:
        """
        List all articles in the specified section
        
        Args:
            book_title: Title of the book
            chapter_title: Title of the chapter
            section_title: Title of the section
            
        Returns:
            ToolResult with article list
        """
        try:
            if not all([book_title, chapter_title, section_title]):
                return ToolResult.failure("Book title, chapter title, and section title are all required.")
            
            # Find the book, chapter, and section
            for book in self._bibliography_data["books"]:
                if book["book_title"].lower() == book_title.lower():
                    for chapter in book["chapters"]:
                        if chapter["chapter_title"].lower() == chapter_title.lower():
                            for section in chapter["sections"]:
                                if section["section_title"].lower() == section_title.lower():
                                    articles = [article["title"] for article in section["articles"]]
                                    
                                    if articles:
                                        message = f"Section '{section_title}' contains the following articles: {', '.join(articles)}."
                                    else:
                                        message = f"Section '{section_title}' has no articles."
                                    
                                    return ToolResult.success(ensure_english_message(message), {
                                        "book_title": book["book_title"],
                                        "chapter_title": chapter["chapter_title"],
                                        "section_title": section["section_title"],
                                        "articles": articles
                                    })
                            
                            return ToolResult.failure(f"Section '{section_title}' not found in chapter '{chapter_title}'.")
                    
                    return ToolResult.failure(f"Chapter '{chapter_title}' not found in book '{book_title}'.")
            
            return ToolResult.failure(f"Book '{book_title}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to list articles: {str(e)}")
    
    def view_article(self, identifier: str, by: str) -> ToolResult:
        """
        View the full content of an article
        
        Args:
            identifier: Article title or ID
            by: Search method - "title" or "id"
            
        Returns:
            ToolResult with article content
        """
        try:
            if not all([identifier, by]):
                return ToolResult.failure("Both identifier and search method ('by') are required.")
            
            if by not in ["title", "id"]:
                return ToolResult.failure("Search method must be either 'title' or 'id'.")
            
            # Search through all articles
            for book in self._bibliography_data["books"]:
                for chapter in book["chapters"]:
                    for section in chapter["sections"]:
                        for article in section["articles"]:
                            if by == "title" and article["title"].lower() == identifier.lower():
                                message = f"Article: {article['title']}\n\n{article['body']}"
                                return ToolResult.success(ensure_english_message(message), article)
                            elif by == "id" and article["article_id"] == identifier:
                                message = f"Article: {article['title']}\n\n{article['body']}"
                                return ToolResult.success(ensure_english_message(message), article)
            
            return ToolResult.failure(f"Article with {by} '{identifier}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to view article: {str(e)}")
    
    # ========== Data System Query Tools ==========
    
    def list_by_category(self, category: str, entity_type: str, level: Optional[str] = None) -> ToolResult:
        """
        List entities by category
        
        Args:
            category: Category to filter by
            entity_type: "club" or "advisor"
            level: For advisors only - "level_1" or "level_2"
            
        Returns:
            ToolResult with matching entities
        """
        try:
            if not all([category, entity_type]):
                return ToolResult.failure("Both category and entity_type are required.")
            
            if entity_type not in ["club", "advisor"]:
                return ToolResult.failure("Entity type must be either 'club' or 'advisor'.")
            
            results = []
            
            if entity_type == "club":
                for club in self._data_system_data["clubs"]:
                    if club["category"].lower() == category.lower():
                        results.append(club["club_name"])
                
                if results:
                    message = f"Clubs in category '{category}': {', '.join(results)}."
                else:
                    message = f"No clubs found in category '{category}'."
                
                return ToolResult.success(ensure_english_message(message), {"clubs": results})
            
            elif entity_type == "advisor":
                for advisor in self._data_system_data["advisors"]:
                    research_area = advisor.get("research_area", {})
                    
                    if level == "level_1" and research_area.get("level_1", "").lower() == category.lower():
                        results.append({
                            "name": advisor["name"],
                            "research_area": research_area,
                            "representative_work": advisor.get("representative_work", [])
                        })
                    elif level == "level_2" and research_area.get("level_2", "").lower() == category.lower():
                        results.append({
                            "name": advisor["name"],
                            "research_area": research_area,
                            "representative_work": advisor.get("representative_work", [])
                        })
                    elif level is None:
                        # Search in both levels and tags
                        if (category.lower() in research_area.get("level_1", "").lower() or
                            category.lower() in research_area.get("level_2", "").lower() or
                            any(category.lower() in tag.lower() for tag in research_area.get("tags", []))):
                            results.append({
                                "name": advisor["name"],
                                "research_area": research_area,
                                "representative_work": advisor.get("representative_work", [])
                            })
                
                if results:
                    message = f"Found {len(results)} advisor(s) in category '{category}':"
                    for advisor in results:
                        message += f"\n- {advisor['name']} (Research: {advisor['research_area'].get('level_2', 'N/A')})"
                else:
                    message = f"No advisors found in category '{category}'."
                
                return ToolResult.success(ensure_english_message(message), {"advisors": results})
            
        except Exception as e:
            return ToolResult.error(f"Failed to list by category: {str(e)}")
    
    def query_by_identifier(self, identifier: str, by: str, entity_type: str) -> ToolResult:
        """
        Query entity by identifier (name or ID)
        
        Args:
            identifier: Entity name or ID
            by: Search method - "name" or "id"
            entity_type: "club" or "advisor"
            
        Returns:
            ToolResult with entity details
        """
        try:
            if not all([identifier, by, entity_type]):
                return ToolResult.failure("Identifier, search method ('by'), and entity_type are all required.")
            
            if by not in ["name", "id"]:
                return ToolResult.failure("Search method must be either 'name' or 'id'.")
            
            if entity_type not in ["club", "advisor"]:
                return ToolResult.failure("Entity type must be either 'club' or 'advisor'.")
            
            if entity_type == "club":
                for club in self._data_system_data["clubs"]:
                    if ((by == "name" and club["club_name"].lower() == identifier.lower()) or
                        (by == "id" and club["club_id"] == identifier)):
                        
                        message = f"Club Details:\n"
                        message += f"Name: {club['club_name']}\n"
                        message += f"ID: {club['club_id']}\n"
                        message += f"Category: {club['category']}\n"
                        message += f"Description: {club['description']}\n"
                        message += f"Recruitment Info: {club['recruitment_info']}"
                        
                        return ToolResult.success(ensure_english_message(message), club)
                
                return ToolResult.failure(f"Club with {by} '{identifier}' not found.")
            
            elif entity_type == "advisor":
                for advisor in self._data_system_data["advisors"]:
                    if ((by == "name" and advisor["name"].lower() == identifier.lower()) or
                        (by == "id" and advisor["advisor_id"] == identifier)):
                        
                        message = f"Advisor Details:\n"
                        message += f"Name: {advisor['name']}\n"
                        message += f"ID: {advisor['advisor_id']}\n"
                        message += f"Email: {advisor['email']}\n"
                        message += f"Research Area: {advisor['research_area']['level_2']}\n"
                        message += f"Representative Work: {', '.join(advisor['representative_work'])}"
                        
                        return ToolResult.success(ensure_english_message(message), advisor)
                
                return ToolResult.failure(f"Advisor with {by} '{identifier}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to query by identifier: {str(e)}")
    
    # ========== Library Books Query Tools ==========
    
    def list_books_by_category(self, category: str) -> ToolResult:
        """
        List all library books by category
        
        Args:
            category: Category to filter by
            
        Returns:
            ToolResult with matching books
        """
        try:
            if not category:
                return ToolResult.failure("Category is required.")
            
            if "library_books" not in self._data_system_data:
                return ToolResult.failure("Library books data not available.")
            
            matching_books = []
            for book in self._data_system_data["library_books"]:
                if book.get("category", "").lower() == category.lower():
                    matching_books.append({
                        "title": book.get("title", ""),
                        "author": book.get("author", ""),
                        "call_number": book.get("call_number", ""),
                        "status": book.get("status", ""),
                        "location": book.get("location", "")
                    })
            
            if matching_books:
                message = f"Found {len(matching_books)} book(s) in category '{category}':"
                for book in matching_books:
                    status_indicator = "✓" if book["status"] == "Available" else "✗"
                    message += f"\n- {status_indicator} \"{book['title']}\" by {book['author']} (Call Number: {book['call_number']})"
            else:
                message = f"No books found in category '{category}'."
            
            return ToolResult.success(ensure_english_message(message), {"books": matching_books})
            
        except Exception as e:
            return ToolResult.error(f"Failed to list books by category: {str(e)}")
    
    def search_books(self, query: str, search_type: str = "title") -> ToolResult:
        """
        Search library books by title or author
        
        Args:
            query: Search query string
            search_type: "title" or "author"
            
        Returns:
            ToolResult with matching books
        """
        try:
            if not query:
                return ToolResult.failure("Search query is required.")
            
            if search_type not in ["title", "author"]:
                return ToolResult.failure("Search type must be either 'title' or 'author'.")
            
            if "library_books" not in self._data_system_data:
                return ToolResult.failure("Library books data not available.")
            
            matching_books = []
            query_lower = query.lower()
            
            for book in self._data_system_data["library_books"]:
                match = False
                if search_type == "title":
                    match = query_lower in book.get("title", "").lower()
                elif search_type == "author":
                    match = query_lower in book.get("author", "").lower()
                
                if match:
                    matching_books.append({
                        "title": book.get("title", ""),
                        "author": book.get("author", ""),
                        "call_number": book.get("call_number", ""),
                        "status": book.get("status", ""),
                        "category": book.get("category", ""),
                        "location": book.get("location", "")
                    })
            
            if matching_books:
                message = f"Found {len(matching_books)} book(s) matching '{query}' in {search_type}:"
                for book in matching_books:
                    status_indicator = "✓" if book["status"] == "Available" else "✗"
                    message += f"\n- {status_indicator} \"{book['title']}\" by {book['author']} ({book['category']}, Call Number: {book['call_number']})"
            else:
                message = f"No books found matching '{query}' in {search_type}."
            
            return ToolResult.success(ensure_english_message(message), {"books": matching_books})
            
        except Exception as e:
            return ToolResult.error(f"Failed to search books: {str(e)}")