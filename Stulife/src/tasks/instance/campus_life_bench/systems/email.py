"""
Email System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from ..tools import ToolResult, ensure_english_message


@dataclass
class SentEmail:
    """Represents a sent email record"""
    recipient: str
    subject: str
    body: str


class EmailSystem:
    """
    Simple email sending system with persistent logging
    Evaluates agent's ability to understand instructions and compose emails
    """
    
    def __init__(self):
        """Initialize the email system"""
        # Global persistent email log
        self._sent_emails_log: List[SentEmail] = []
    
    def send_email(self, recipient: str, subject: str, body: str) -> ToolResult:
        """
        Send an email to the specified recipient
        
        Args:
            recipient: Email address of the recipient
            subject: Email subject line
            body: Email body content
            
        Returns:
            ToolResult indicating success or failure
        """
        try:
            # Validate all parameters are provided and non-empty
            if not recipient or not isinstance(recipient, str):
                return ToolResult.failure("Recipient email address is required and must be a non-empty string.")
            
            if not subject or not isinstance(subject, str):
                return ToolResult.failure("Email subject is required and must be a non-empty string.")
            
            if not body or not isinstance(body, str):
                return ToolResult.failure("Email body is required and must be a non-empty string.")
            
            # Basic email format validation
            if "@" not in recipient or "." not in recipient:
                return ToolResult.failure("Invalid email address format.")
            
            # Create email record
            email = SentEmail(
                recipient=recipient.strip(),
                subject=subject.strip(),
                body=body.strip()
            )
            
            # Add to persistent log
            self._sent_emails_log.append(email)
            
            message = f"Email has been successfully sent to {recipient}."
            return ToolResult.success(ensure_english_message(message), {
                "recipient": email.recipient,
                "subject": email.subject,
                "email_count": len(self._sent_emails_log)
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to send email: {str(e)}")
    
    def get_sent_emails_for_evaluation(self) -> List[SentEmail]:
        """
        Get all sent emails for evaluation purposes
        Used by CampusTask during evaluation
        
        Returns:
            List of SentEmail objects
        """
        return self._sent_emails_log.copy()
    
    def get_latest_email_for_evaluation(self) -> SentEmail:
        """
        Get the most recently sent email for evaluation
        Used by CampusTask during evaluation
        
        Returns:
            Most recent SentEmail object or None if no emails sent
        """
        if self._sent_emails_log:
            return self._sent_emails_log[-1]
        return None
    
    def clear_emails(self) -> None:
        """
        Clear all sent emails (for testing purposes only)
        Should not be used in normal operation
        """
        self._sent_emails_log.clear()
    
    def get_email_count(self) -> int:
        """
        Get total number of emails sent
        
        Returns:
            Number of emails in the log
        """
        return len(self._sent_emails_log)
