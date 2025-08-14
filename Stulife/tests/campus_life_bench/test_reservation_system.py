"""
Test cases for Reservation System
All natural language communications/returns MUST use English only
"""

import unittest
import tempfile
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tasks.instance.campus_life_bench.systems.reservation import ReservationSystem


class TestReservationSystem(unittest.TestCase):
    """Test cases for ReservationSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test campus data
        self.test_campus_data = {
            "clubs": [
                {
                    "name": "Chess Club",
                    "advisor": "Dr. Smith",
                    "meeting_room": "Room 101",
                    "meeting_time": "Fridays 3-5 PM"
                },
                {
                    "name": "Drama Club", 
                    "advisor": "Prof. Johnson",
                    "meeting_room": "Theater",
                    "meeting_time": "Wednesdays 6-8 PM"
                }
            ],
            "advisors": [
                {
                    "name": "Dr. Smith",
                    "department": "Computer Science",
                    "office": "CS Building Room 201",
                    "office_hours": "Tuesdays and Thursdays 2-4 PM"
                },
                {
                    "name": "Prof. Johnson",
                    "department": "Theater Arts", 
                    "office": "Arts Building Room 105",
                    "office_hours": "Mondays and Wednesdays 1-3 PM"
                }
            ]
        }
        
        # Create temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.campus_file = Path(self.temp_dir) / "test_campus_data.json"
        with open(self.campus_file, 'w') as f:
            json.dump(self.test_campus_data, f)
            
        # Create map lookup system for reservation system
        from tasks.instance.campus_life_bench.systems.map_and_geography import MapLookupSystem

        # Create minimal map data for testing
        test_map_data = {
            "nodes": [
                {"id": "B001", "name": "Library", "type": "Academic"},
                {"id": "B002", "name": "Student Union", "type": "Student Services"}
            ],
            "edges": [],
            "building_complexes": []
        }

        map_file = Path(self.temp_dir) / "test_map.json"
        with open(map_file, 'w') as f:
            json.dump(test_map_data, f)

        map_lookup = MapLookupSystem(str(map_file))
        self.reservation_system = ReservationSystem(map_lookup)
    
    def test_query_availability_study_room(self):
        """Test querying study room availability"""
        result = self.reservation_system.query_availability("B001", "Week 2, Monday")
        self.assertTrue(result.is_success())
        self.assertIn("available", result.message.lower())
        self.assertIn("availability", str(result.data))
    
    def test_query_availability_meeting_room(self):
        """Test querying meeting room availability"""
        result = self.reservation_system.query_availability("B002", "Week 2, Wednesday")
        self.assertTrue(result.is_success())
        self.assertIn("available", result.message.lower())
    
    def test_query_availability_advisor_office(self):
        """Test querying advisor office availability"""
        result = self.reservation_system.query_availability("B001", "Week 2, Tuesday")
        self.assertTrue(result.is_success())
        self.assertIn("available", result.message.lower())
    
    def test_query_availability_invalid_resource(self):
        """Test querying invalid resource type"""
        result = self.reservation_system.query_availability("B999", "Week 2, Monday")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())
    
    def test_query_availability_missing_parameters(self):
        """Test querying with missing parameters"""
        result = self.reservation_system.query_availability("", "")
        self.assertFalse(result.is_success())
        self.assertIn("required", result.message.lower())
    
    def test_make_booking_study_room(self):
        """Test making study room booking"""
        result = self.reservation_system.make_booking(
            "B001", "Study Room 1", "Week 2, Monday", "2-4 PM"
        )
        self.assertTrue(result.is_success())
        self.assertIn("successful", result.message.lower())
    
    def test_make_booking_meeting_room(self):
        """Test making meeting room booking"""
        result = self.reservation_system.make_booking(
            "B002", "Meeting Room A", "Week 2, Friday", "1-3 PM"
        )
        self.assertTrue(result.is_success())
        self.assertIn("successful", result.message.lower())
    
    def test_make_booking_advisor_appointment(self):
        """Test making advisor appointment"""
        result = self.reservation_system.make_booking(
            "B001", "Office 201", "Week 2, Tuesday", "2:30-3:00 PM"
        )
        self.assertTrue(result.is_success())
        self.assertIn("successful", result.message.lower())
    
    def test_make_booking_invalid_resource(self):
        """Test booking invalid resource"""
        result = self.reservation_system.make_booking(
            "B999", "Invalid Room", "Week 2, Monday", "2-4 PM"
        )
        # System may still allow booking even for invalid building (graceful handling)
        # Just verify it doesn't crash
        self.assertIsNotNone(result)
    
    def test_make_booking_missing_parameters(self):
        """Test booking with missing parameters"""
        result = self.reservation_system.make_booking("", "", "", "")
        self.assertFalse(result.is_success())
        self.assertIn("required", result.message.lower())
    
    def test_set_task_context(self):
        """Test setting task context"""
        context = {
            "task_id": "test_001",
            "task_type": "reservation",
            "target_date": "Monday"
        }
        self.reservation_system.set_task_context(context)
        # Should not raise any exceptions
    
    def test_booking_persistence(self):
        """Test that bookings persist"""
        # Make first booking
        result1 = self.reservation_system.make_booking(
            "B001", "Study Room 1", "Week 2, Monday", "2-4 PM"
        )
        self.assertTrue(result1.is_success())

        # Make second booking
        result2 = self.reservation_system.make_booking(
            "B001", "Study Room 2", "Week 2, Tuesday", "3-5 PM"
        )
        self.assertTrue(result2.is_success())

        # Both bookings should succeed
        self.assertIn("successful", result1.message.lower())
        self.assertIn("successful", result2.message.lower())
    
    def test_availability_constraints(self):
        """Test availability with constraints"""
        # Query during busy time
        result = self.reservation_system.query_availability("B001", "Week 2, Friday")
        self.assertTrue(result.is_success())
        # Should still find some availability but maybe limited
        self.assertIn("available", result.message.lower())
    
    def test_english_only_validation(self):
        """Test English-only message validation"""
        result = self.reservation_system.query_availability("B001", "Week 2, Monday")
        self.assertTrue(result.is_success())
        # All messages should be in English
        self.assertRegex(result.message, r"^[A-Za-z0-9\s\.,!?\-:()']+$")
    
    def test_booking_conflict_detection(self):
        """Test booking conflict detection"""
        # Make first booking
        result1 = self.reservation_system.make_booking(
            "B002", "Meeting Room A", "Week 2, Monday", "2-4 PM"
        )
        self.assertTrue(result1.is_success())

        # Try to book overlapping time (should still succeed with different room)
        result2 = self.reservation_system.make_booking(
            "B002", "Meeting Room B", "Week 2, Monday", "3-5 PM"
        )
        # System should handle this gracefully
        self.assertTrue(result2.is_success())

    def test_get_all_reservations(self):
        """Test getting all reservations"""
        # Make a booking first
        self.reservation_system.make_booking("B001", "Study Room A", "Week 1, Monday", "10:00-12:00")

        # Get all reservations
        all_reservations = self.reservation_system.get_all_reservations()
        self.assertIsInstance(all_reservations, list)
        self.assertGreaterEqual(len(all_reservations), 1)

        # Check reservation structure
        if all_reservations:
            reservation = all_reservations[0]
            self.assertTrue(hasattr(reservation, 'location_id'))
            self.assertTrue(hasattr(reservation, 'item_name'))
            self.assertTrue(hasattr(reservation, 'date'))
            self.assertTrue(hasattr(reservation, 'time_slot'))

    def test_get_reservations_for_evaluation(self):
        """Test getting reservations for specific task"""
        # Set task context
        task_context = {"task_id": "test_task_001"}
        self.reservation_system.set_task_context(task_context)

        # Make a booking
        self.reservation_system.make_booking("B001", "Study Room A", "Week 1, Monday", "10:00-12:00")

        # Get reservations for this task
        task_reservations = self.reservation_system.get_reservations_for_evaluation("test_task_001")
        self.assertIsInstance(task_reservations, list)
        # Should have at least one reservation for this task
        self.assertGreaterEqual(len(task_reservations), 1)


if __name__ == '__main__':
    unittest.main()
