"""
Unit tests for Calendar System
All natural language communications/returns MUST use English only
"""

import unittest
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tasks.instance.campus_life_bench.systems.world_and_calendar import CalendarSystem, WorldTimeSystem
from tasks.instance.campus_life_bench.tools import ToolResult, ToolResultStatus


class TestWorldTimeSystem(unittest.TestCase):
    """Test cases for WorldTimeSystem"""
    
    def test_generate_daily_announcement(self):
        """Test daily announcement generation"""
        announcement = WorldTimeSystem.generate_daily_announcement("Week 2, Saturday")
        
        self.assertIn("Today is Week 2, Saturday", announcement)
        self.assertTrue(announcement.startswith("System Announcement:"))
    
    def test_generate_time_prompt(self):
        """Test time prompt generation"""
        # Test morning time
        prompt = WorldTimeSystem.generate_time_prompt("08:00")
        self.assertIn("8:00 AM", prompt)
        
        # Test afternoon time
        prompt = WorldTimeSystem.generate_time_prompt("14:30")
        self.assertIn("2:30 PM", prompt)
        
        # Test midnight
        prompt = WorldTimeSystem.generate_time_prompt("00:00")
        self.assertIn("12:00 AM", prompt)
        
        # Test noon
        prompt = WorldTimeSystem.generate_time_prompt("12:00")
        self.assertIn("12:00 PM", prompt)


class TestCalendarSystem(unittest.TestCase):
    """Test cases for CalendarSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calendar_system = CalendarSystem()
    
    def test_add_event_success(self):
        """Test successful event addition"""
        result = self.calendar_system.add_event(
            calendar_id="self",
            event_title="Study Session",
            location="Library",
            time="Week 1, Monday, 14:00-16:00"
        )
        
        self.assertTrue(result.is_success())
        self.assertIn("successfully added", result.message)
        self.assertIsNotNone(result.data["event_id"])
    
    def test_add_event_missing_parameters(self):
        """Test event addition with missing parameters"""
        result = self.calendar_system.add_event(
            calendar_id="self",
            event_title="",
            location="Library",
            time="Week 1, Monday, 14:00-16:00"
        )
        
        self.assertTrue(result.is_failure())
        self.assertIn("required", result.message)
    
    def test_add_event_permission_denied(self):
        """Test event addition with insufficient permissions"""
        result = self.calendar_system.add_event(
            calendar_id="advisor_T001",
            event_title="Meeting",
            location="Office",
            time="Week 1, Monday, 14:00-16:00"
        )
        
        self.assertTrue(result.is_failure())
        self.assertIn("permission", result.message)
    
    def test_remove_event_success(self):
        """Test successful event removal"""
        # First add an event
        add_result = self.calendar_system.add_event(
            calendar_id="self",
            event_title="Study Session",
            location="Library",
            time="Week 1, Monday, 14:00-16:00"
        )
        event_id = add_result.data["event_id"]
        
        # Then remove it
        remove_result = self.calendar_system.remove_event("self", event_id)
        
        self.assertTrue(remove_result.is_success())
        self.assertIn("successfully removed", remove_result.message)
    
    def test_remove_event_not_found(self):
        """Test removing non-existent event"""
        result = self.calendar_system.remove_event("self", "non_existent_id")
        
        self.assertTrue(result.is_failure())
        self.assertIn("not found", result.message)
    
    def test_remove_event_permission_denied(self):
        """Test removing event with insufficient permissions"""
        result = self.calendar_system.remove_event("club_c001", "some_id")
        
        self.assertTrue(result.is_failure())
        self.assertIn("permission", result.message)
    
    def test_update_event_success(self):
        """Test successful event update"""
        # First add an event
        add_result = self.calendar_system.add_event(
            calendar_id="self",
            event_title="Study Session",
            location="Library",
            time="Week 1, Monday, 14:00-16:00"
        )
        event_id = add_result.data["event_id"]
        
        # Then update it
        update_result = self.calendar_system.update_event(
            calendar_id="self",
            event_id=event_id,
            new_details={"event_title": "Updated Study Session"}
        )
        
        self.assertTrue(update_result.is_success())
        self.assertIn("successfully updated", update_result.message)
    
    def test_view_schedule_empty(self):
        """Test viewing empty schedule"""
        result = self.calendar_system.view_schedule("self", "Week 1, Monday")
        
        self.assertTrue(result.is_success())
        self.assertIn("No events found", result.message)
    
    def test_view_schedule_with_events(self):
        """Test viewing schedule with events"""
        # Add an event
        self.calendar_system.add_event(
            calendar_id="self",
            event_title="Study Session",
            location="Library",
            time="Week 1, Monday, 14:00-16:00"
        )
        
        # View schedule
        result = self.calendar_system.view_schedule("self", "Week 1, Monday")
        
        self.assertTrue(result.is_success())
        self.assertIn("Study Session", result.message)
        self.assertIn("Library", result.message)
    
    def test_view_schedule_permission_denied(self):
        """Test viewing schedule with insufficient permissions"""
        result = self.calendar_system.view_schedule("advisor_T001", "Week 1, Monday")
        
        self.assertTrue(result.is_failure())
        self.assertIn("permission", result.message)
    
    def test_query_advisor_availability(self):
        """Test querying advisor availability"""
        result = self.calendar_system.query_advisor_availability("T001", "Week 1, Monday")
        
        self.assertTrue(result.is_success())
        self.assertIn("available", result.message)
        self.assertIsInstance(result.data["available_slots"], list)
    
    def test_club_calendar_permissions(self):
        """Test club calendar permissions"""
        # Should be able to add to club calendar
        result = self.calendar_system.add_event(
            calendar_id="club_c001",
            event_title="Club Meeting",
            location="Meeting Room",
            time="Week 1, Friday, 18:00-19:00"
        )
        
        self.assertTrue(result.is_success())
        
        # Should be able to view club calendar
        view_result = self.calendar_system.view_schedule("club_c001", "Week 1, Friday")
        self.assertTrue(view_result.is_success())
        
        # Should NOT be able to remove from club calendar
        event_id = result.data["event_id"]
        remove_result = self.calendar_system.remove_event("club_c001", event_id)
        self.assertTrue(remove_result.is_failure())
    
    def test_get_calendar_events_for_evaluation(self):
        """Test getting calendar events for evaluation"""
        # Add some events
        self.calendar_system.add_event(
            calendar_id="self",
            event_title="Event 1",
            location="Location 1",
            time="Week 1, Monday, 10:00-11:00"
        )
        
        self.calendar_system.add_event(
            calendar_id="self",
            event_title="Event 2",
            location="Location 2",
            time="Week 1, Tuesday, 14:00-15:00"
        )
        
        # Get events for evaluation
        events = self.calendar_system.get_calendar_events_for_evaluation("self")
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_title, "Event 1")
        self.assertEqual(events[1].event_title, "Event 2")
    
    def test_english_only_validation(self):
        """Test that all messages are in English"""
        result = self.calendar_system.add_event(
            calendar_id="self",
            event_title="Study Session",
            location="Library",
            time="Week 1, Monday, 14:00-16:00"
        )
        
        # Check that message contains only English characters
        message = result.message
        self.assertTrue(all(ord(char) < 128 for char in message), 
                       "Message should contain only ASCII characters")


if __name__ == "__main__":
    unittest.main()
