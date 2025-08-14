"""
Unit tests for Email System
All natural language communications/returns MUST use English only
"""

import unittest
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tasks.instance.campus_life_bench.systems.email import EmailSystem
from tasks.instance.campus_life_bench.tools import ToolResult, ToolResultStatus


class TestEmailSystem(unittest.TestCase):
    """Test cases for EmailSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.email_system = EmailSystem()
    
    def test_send_email_success(self):
        """Test successful email sending"""
        result = self.email_system.send_email(
            recipient="test@university.edu",
            subject="Test Subject",
            body="Test body content"
        )
        
        self.assertTrue(result.is_success())
        self.assertIn("successfully sent", result.message)
        self.assertEqual(len(self.email_system.get_sent_emails_for_evaluation()), 1)
    
    def test_send_email_missing_recipient(self):
        """Test email sending with missing recipient"""
        result = self.email_system.send_email(
            recipient="",
            subject="Test Subject", 
            body="Test body"
        )
        
        self.assertTrue(result.is_failure())
        self.assertIn("required", result.message)
    
    def test_send_email_missing_subject(self):
        """Test email sending with missing subject"""
        result = self.email_system.send_email(
            recipient="test@university.edu",
            subject="",
            body="Test body"
        )
        
        self.assertTrue(result.is_failure())
        self.assertIn("required", result.message)
    
    def test_send_email_missing_body(self):
        """Test email sending with missing body"""
        result = self.email_system.send_email(
            recipient="test@university.edu",
            subject="Test Subject",
            body=""
        )
        
        self.assertTrue(result.is_failure())
        self.assertIn("required", result.message)
    
    def test_send_email_invalid_format(self):
        """Test email sending with invalid email format"""
        result = self.email_system.send_email(
            recipient="invalid-email",
            subject="Test Subject",
            body="Test body"
        )
        
        self.assertTrue(result.is_failure())
        self.assertIn("Invalid email address", result.message)
    
    def test_multiple_emails(self):
        """Test sending multiple emails"""
        # Send first email
        result1 = self.email_system.send_email(
            recipient="test1@university.edu",
            subject="Subject 1",
            body="Body 1"
        )
        self.assertTrue(result1.is_success())
        
        # Send second email
        result2 = self.email_system.send_email(
            recipient="test2@university.edu", 
            subject="Subject 2",
            body="Body 2"
        )
        self.assertTrue(result2.is_success())
        
        # Check both emails are stored
        emails = self.email_system.get_sent_emails_for_evaluation()
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].recipient, "test1@university.edu")
        self.assertEqual(emails[1].recipient, "test2@university.edu")
    
    def test_get_latest_email(self):
        """Test getting the latest email"""
        # No emails initially
        latest = self.email_system.get_latest_email_for_evaluation()
        self.assertIsNone(latest)
        
        # Send an email
        self.email_system.send_email(
            recipient="test@university.edu",
            subject="Test Subject",
            body="Test body"
        )
        
        # Check latest email
        latest = self.email_system.get_latest_email_for_evaluation()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.recipient, "test@university.edu")
        self.assertEqual(latest.subject, "Test Subject")
        self.assertEqual(latest.body, "Test body")
    
    def test_email_count(self):
        """Test email count tracking"""
        self.assertEqual(self.email_system.get_email_count(), 0)
        
        self.email_system.send_email("test1@university.edu", "Subject 1", "Body 1")
        self.assertEqual(self.email_system.get_email_count(), 1)
        
        self.email_system.send_email("test2@university.edu", "Subject 2", "Body 2")
        self.assertEqual(self.email_system.get_email_count(), 2)
    
    def test_clear_emails(self):
        """Test clearing emails (for testing purposes)"""
        # Send some emails
        self.email_system.send_email("test1@university.edu", "Subject 1", "Body 1")
        self.email_system.send_email("test2@university.edu", "Subject 2", "Body 2")
        self.assertEqual(self.email_system.get_email_count(), 2)
        
        # Clear emails
        self.email_system.clear_emails()
        self.assertEqual(self.email_system.get_email_count(), 0)
        self.assertIsNone(self.email_system.get_latest_email_for_evaluation())
    
    def test_english_only_validation(self):
        """Test that all messages are in English"""
        result = self.email_system.send_email(
            recipient="test@university.edu",
            subject="Test Subject",
            body="Test body content"
        )
        
        # Check that message contains only English characters
        message = result.message
        self.assertTrue(all(ord(char) < 128 for char in message), 
                       "Message should contain only ASCII characters")
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in email fields"""
        result = self.email_system.send_email(
            recipient="  test@university.edu  ",
            subject="  Test Subject  ",
            body="  Test body content  "
        )
        
        self.assertTrue(result.is_success())
        
        latest = self.email_system.get_latest_email_for_evaluation()
        self.assertEqual(latest.recipient, "test@university.edu")  # Stripped
        self.assertEqual(latest.subject, "Test Subject")  # Stripped
        self.assertEqual(latest.body, "Test body content")  # Stripped


if __name__ == "__main__":
    unittest.main()
