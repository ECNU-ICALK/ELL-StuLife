import unittest
import sys
import os
from pathlib import Path
import json

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / 'LifelongAgentBench-main'))

from src.tasks.instance.campus_life_bench.systems.reservation import ReservationSystem
from src.tasks.instance.campus_life_bench.systems.map_and_geography import MapLookupSystem
from src.tasks.instance.campus_life_bench.systems.information import InformationSystem

class TestReservationSystem(unittest.TestCase):

    def setUp(self):
        """Set up the test environment before each test."""
        # Define paths relative to the test file
        test_dir = Path(__file__).parent
        self.data_dir = project_root / 'task_data' / 'background'
        
        # Ensure data files exist
        map_path = self.data_dir / "map_v1.5.json"
        campus_data_path = self.data_dir / "campus_data.json"
        bibliography_path = self.data_dir / "bibliography.json"

        self.assertTrue(map_path.exists(), f"Map data not found at {map_path}")
        self.assertTrue(campus_data_path.exists(), f"Campus data not found at {campus_data_path}")

        # Initialize systems
        self.map_lookup = MapLookupSystem(map_path)
        self.info_system = InformationSystem(bibliography_path, campus_data_path)
        self.reservation_system = ReservationSystem(
            map_lookup_system=self.map_lookup,
            information_system=self.info_system
        )

    def test_query_availability_returns_real_seat_ids(self):
        """
        Test that query_availability returns real, correctly formatted seat IDs.
        """
        # 1. Define a mock task context similar to a real task
        mock_task_context = {
            "task_id": "test_task_dpskv3",
            "details": {
                "implied_requirements": ["power_outlet", "quiet_zone"]
            },
            "ground_truth": {
                "item_name": "3D Printing Lab",
                "location_id": "B042"
            }
        }
        self.reservation_system.set_task_context(mock_task_context)

        # 2. Get building details for B042 (STEM Library)
        building_result = self.map_lookup.get_building_details("B042")
        self.assertTrue(building_result.is_success(), "Failed to get building details for B042")
        building_data = building_result.data

        # 3. Call the method to test
        result = self.reservation_system.query_availability(location_id="B042", date="Week 2, Friday")

        # 4. Assert the results
        self.assertTrue(result.is_success(), f"Query availability failed: {result.message}")
        
        # Check that the message contains a real seat ID
        # A real seat ID for this lab should be in the format B042-101-SXXX
        self.assertIn("B042-101-S", result.message, 
                      "The output message does not contain a correctly formatted real seat ID.")
        
        # Check that the output is not just "Facility: seats (Available)"
        self.assertNotIn("Facility: seats (Available)", result.message,
                         "The output message incorrectly shows 'seats (Available)' instead of listing seat IDs.")

if __name__ == '__main__':
    unittest.main()
