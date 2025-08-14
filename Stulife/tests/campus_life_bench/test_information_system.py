"""
Test cases for Information System (Bibliography and Campus Data)
All natural language communications/returns MUST use English only
"""

import unittest
import tempfile
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tasks.instance.campus_life_bench.systems.information import InformationSystem


class TestInformationSystem(unittest.TestCase):
    """Test cases for InformationSystem"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test bibliography data matching actual format
        self.test_bibliography = {
            "books": [
                {
                    "book_title": "Introduction to Computer Science",
                    "author": "John Smith",
                    "isbn": "978-0123456789",
                    "publication_year": 2020,
                    "publisher": "Tech Publications",
                    "chapters": [
                        {
                            "chapter_title": "Programming Fundamentals",
                            "sections": [
                                {
                                    "section_title": "Basic Concepts",
                                    "articles": [
                                        {
                                            "article_title": "Variables and Data Types",
                                            "article_id": "art_001",
                                            "title": "Variables and Data Types",
                                            "body": "This article covers variables and data types in programming."
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "chapter_title": "Data Structures",
                            "sections": [
                                {
                                    "section_title": "Arrays and Lists",
                                    "articles": [
                                        {
                                            "article_title": "Array Operations",
                                            "article_id": "art_002",
                                            "title": "Array Operations",
                                            "body": "This article explains array operations and manipulations."
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "book_title": "Advanced Mathematics",
                    "author": "Jane Doe",
                    "isbn": "978-0987654321",
                    "publication_year": 2019,
                    "publisher": "Academic Press",
                    "chapters": [
                        {
                            "chapter_title": "Calculus Review",
                            "sections": [
                                {
                                    "section_title": "Derivatives",
                                    "articles": [
                                        {
                                            "article_title": "Basic Derivatives",
                                            "article_id": "art_003",
                                            "title": "Basic Derivatives",
                                            "body": "This article covers basic derivative calculations and rules."
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Create test campus data matching actual format
        self.test_campus_data = {
            "clubs": [
                {
                    "club_id": "C001",
                    "club_name": "Chess Club",
                    "category": "Academic",
                    "description": "Weekly chess tournaments and strategy discussions",
                    "recruitment_info": "Open to all students interested in chess"
                },
                {
                    "club_id": "C002",
                    "club_name": "Drama Club",
                    "category": "Arts",
                    "description": "Theater performances and acting workshops",
                    "recruitment_info": "Auditions held every semester"
                }
            ],
            "advisors": [
                {
                    "advisor_id": "T001",
                    "name": "Dr. Smith",
                    "gender": "Male",
                    "age": 45,
                    "email": "dr.smith@university.edu",
                    "research_area": {
                        "level_1": "Computer Science",
                        "level_2": "Artificial Intelligence",
                        "tags": ["Machine Learning", "Natural Language Processing"]
                    },
                    "representative_work": ["AI in Education", "NLP Applications"],
                    "preferences": {"meeting_time": "afternoon", "communication": "email"}
                },
                {
                    "advisor_id": "T002",
                    "name": "Prof. Johnson",
                    "gender": "Female",
                    "age": 38,
                    "email": "prof.johnson@university.edu",
                    "research_area": {
                        "level_1": "Theater Arts",
                        "level_2": "Performance Studies",
                        "tags": ["Acting", "Directing"]
                    },
                    "representative_work": ["Modern Theater", "Performance Theory"],
                    "preferences": {"meeting_time": "morning", "communication": "in-person"}
                }
            ]
        }
        
        # Create temporary files
        self.temp_dir = tempfile.mkdtemp()
        self.bibliography_file = Path(self.temp_dir) / "test_bibliography.json"
        self.campus_file = Path(self.temp_dir) / "test_campus_data.json"
        
        with open(self.bibliography_file, 'w') as f:
            json.dump(self.test_bibliography, f)
        with open(self.campus_file, 'w') as f:
            json.dump(self.test_campus_data, f)
            
        self.info_system = InformationSystem(
            str(self.bibliography_file), 
            str(self.campus_file)
        )
    
    def test_list_chapters_valid_book(self):
        """Test listing chapters for valid book"""
        result = self.info_system.list_chapters("Introduction to Computer Science")
        self.assertTrue(result.is_success())
        self.assertIn("chapters", result.data)
        self.assertEqual(len(result.data["chapters"]), 2)
        self.assertIn("Programming Fundamentals", result.data["chapters"])
        self.assertIn("Data Structures", result.data["chapters"])

    def test_list_chapters_invalid_book(self):
        """Test listing chapters for invalid book title"""
        result = self.info_system.list_chapters("Nonexistent Book")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())

    def test_list_chapters_empty_title(self):
        """Test listing chapters with empty title"""
        result = self.info_system.list_chapters("")
        self.assertFalse(result.is_success())
        self.assertIn("required", result.message.lower())

    def test_list_sections_valid_chapter(self):
        """Test listing sections for valid chapter"""
        result = self.info_system.list_sections("Introduction to Computer Science", "Programming Fundamentals")
        self.assertTrue(result.is_success())
        self.assertIn("sections", result.data)
        self.assertIn("Basic Concepts", result.data["sections"])

    def test_list_sections_invalid_book(self):
        """Test listing sections for invalid book"""
        result = self.info_system.list_sections("Nonexistent Book", "Some Chapter")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())

    def test_list_sections_invalid_chapter(self):
        """Test listing sections for invalid chapter"""
        result = self.info_system.list_sections("Introduction to Computer Science", "Nonexistent Chapter")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())
    
    def test_list_articles_valid_section(self):
        """Test listing articles for valid section"""
        result = self.info_system.list_articles("Introduction to Computer Science", "Programming Fundamentals", "Basic Concepts")
        self.assertTrue(result.is_success())
        self.assertIn("articles", result.data)
        # Articles are returned as title strings, not objects
        self.assertIn("Variables and Data Types", result.data["articles"])

    def test_list_articles_invalid_book(self):
        """Test listing articles for invalid book"""
        result = self.info_system.list_articles("Nonexistent Book", "Some Chapter", "Some Section")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())

    def test_list_articles_invalid_chapter(self):
        """Test listing articles for invalid chapter"""
        result = self.info_system.list_articles("Introduction to Computer Science", "Nonexistent Chapter", "Some Section")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())

    def test_list_articles_invalid_section(self):
        """Test listing articles for invalid section"""
        result = self.info_system.list_articles("Introduction to Computer Science", "Programming Fundamentals", "Nonexistent Section")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())

    def test_view_article_by_title(self):
        """Test viewing article by title"""
        result = self.info_system.view_article("Variables and Data Types", "title")
        self.assertTrue(result.is_success())
        self.assertIn("body", result.data)
        self.assertIn("Variables and Data Types", result.data["title"])

    def test_view_article_by_id(self):
        """Test viewing article by ID"""
        result = self.info_system.view_article("art_001", "id")
        self.assertTrue(result.is_success())
        self.assertIn("body", result.data)
        self.assertIn("Variables and Data Types", result.data["title"])

    def test_view_article_invalid_method(self):
        """Test viewing article with invalid method"""
        result = self.info_system.view_article("Variables and Data Types", "invalid")
        self.assertFalse(result.is_success())
        self.assertIn("must be either 'title' or 'id'", result.message.lower())
    
    def test_list_by_category_clubs(self):
        """Test listing clubs by category"""
        result = self.info_system.list_by_category("Academic", "club")
        self.assertTrue(result.is_success())
        self.assertIn("clubs", result.data)
        self.assertGreater(len(result.data["clubs"]), 0)
        # Check if clubs are returned as strings or objects
        if isinstance(result.data["clubs"][0], str):
            self.assertIn("Chess Club", result.data["clubs"])
        else:
            self.assertEqual(result.data["clubs"][0]["club_name"], "Chess Club")

    def test_list_by_category_advisors_level1(self):
        """Test listing level 1 advisors"""
        result = self.info_system.list_by_category("Computer Science", "advisor", "level_1")
        self.assertTrue(result.is_success())
        self.assertIn("advisors", result.data)
        self.assertGreater(len(result.data["advisors"]), 0)

    def test_list_by_category_advisors_level2(self):
        """Test listing level 2 advisors"""
        result = self.info_system.list_by_category("Performance Studies", "advisor", "level_2")
        self.assertTrue(result.is_success())
        self.assertIn("advisors", result.data)
        self.assertGreater(len(result.data["advisors"]), 0)

    def test_list_by_category_invalid_entity_type(self):
        """Test listing with invalid entity type"""
        result = self.info_system.list_by_category("Academic", "invalid")
        self.assertFalse(result.is_success())
        self.assertIn("must be either 'club' or 'advisor'", result.message.lower())

    def test_query_by_identifier_club_by_name(self):
        """Test querying club by name"""
        result = self.info_system.query_by_identifier("Chess Club", "name", "club")
        self.assertTrue(result.is_success())
        self.assertIn("Chess Club", result.data["club_name"])
        self.assertIn("category", result.data)

    def test_query_by_identifier_club_by_id(self):
        """Test querying club by ID"""
        result = self.info_system.query_by_identifier("C001", "id", "club")
        self.assertTrue(result.is_success())
        self.assertIn("Chess Club", result.data["club_name"])

    def test_query_by_identifier_advisor_by_name(self):
        """Test querying advisor by name"""
        result = self.info_system.query_by_identifier("Dr. Smith", "name", "advisor")
        self.assertTrue(result.is_success())
        self.assertIn("Dr. Smith", result.data["name"])
        self.assertIn("research_area", result.data)

    def test_query_by_identifier_advisor_by_id(self):
        """Test querying advisor by ID"""
        result = self.info_system.query_by_identifier("T001", "id", "advisor")
        self.assertTrue(result.is_success())
        self.assertIn("Dr. Smith", result.data["name"])

    def test_query_by_identifier_not_found(self):
        """Test querying non-existent entity"""
        result = self.info_system.query_by_identifier("Nonexistent", "name", "club")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())

    def test_query_by_identifier_invalid_method(self):
        """Test querying with invalid method"""
        result = self.info_system.query_by_identifier("Chess Club", "invalid", "club")
        self.assertFalse(result.is_success())
        self.assertIn("must be either 'name' or 'id'", result.message.lower())

    def test_query_by_identifier_invalid_entity_type(self):
        """Test querying with invalid entity type"""
        result = self.info_system.query_by_identifier("Chess Club", "name", "invalid")
        self.assertFalse(result.is_success())
        self.assertIn("must be either 'club' or 'advisor'", result.message.lower())
    
    def test_english_only_validation(self):
        """Test English-only message validation"""
        result = self.info_system.list_chapters("Introduction to Computer Science")
        self.assertTrue(result.is_success())
        # All messages should be in English
        self.assertRegex(result.message, r"^[A-Za-z0-9\s\.,!?\-:()']+$")

    def test_case_insensitive_searches(self):
        """Test case insensitive searches"""
        # Test book title case insensitivity
        result1 = self.info_system.list_chapters("introduction to computer science")
        self.assertTrue(result1.is_success())

        result2 = self.info_system.list_chapters("INTRODUCTION TO COMPUTER SCIENCE")
        self.assertTrue(result2.is_success())

        # Both should return same results
        self.assertEqual(result1.data["chapters"], result2.data["chapters"])

    def test_article_content_generation(self):
        """Test that article content is properly generated"""
        result = self.info_system.view_article("Variables and Data Types", "title")
        self.assertTrue(result.is_success())
        self.assertIn("body", result.data)
        self.assertIsInstance(result.data["body"], str)
        self.assertGreater(len(result.data["body"]), 0)

    def test_empty_parameter_validation(self):
        """Test validation of empty parameters"""
        # Test empty book title
        result = self.info_system.list_chapters("")
        self.assertFalse(result.is_success())

        # Test empty chapter title
        result = self.info_system.list_sections("Introduction to Computer Science", "")
        self.assertFalse(result.is_success())

        # Test empty section title
        result = self.info_system.list_articles("Introduction to Computer Science", "Programming Fundamentals", "")
        self.assertFalse(result.is_success())

    def test_data_structure_consistency(self):
        """Test that returned data structures are consistent"""
        # Test chapters list structure
        result = self.info_system.list_chapters("Introduction to Computer Science")
        self.assertTrue(result.is_success())
        self.assertIn("book_title", result.data)
        self.assertIn("chapters", result.data)
        self.assertIsInstance(result.data["chapters"], list)

        # Test sections list structure
        result = self.info_system.list_sections("Introduction to Computer Science", "Programming Fundamentals")
        self.assertTrue(result.is_success())
        self.assertIn("sections", result.data)
        self.assertIsInstance(result.data["sections"], list)

        # Test articles list structure
        result = self.info_system.list_articles("Introduction to Computer Science", "Programming Fundamentals", "Basic Concepts")
        self.assertTrue(result.is_success())
        self.assertIn("articles", result.data)
        self.assertIsInstance(result.data["articles"], list)
        # Articles are returned as title strings
        for article in result.data["articles"]:
            self.assertIsInstance(article, str)


if __name__ == '__main__':
    unittest.main()
