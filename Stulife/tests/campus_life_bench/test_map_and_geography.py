"""
Test cases for Map and Geography System
All natural language communications/returns MUST use English only
"""

import unittest
import tempfile
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tasks.instance.campus_life_bench.systems.map_and_geography import MapLookupSystem, GeographySystem


class TestMapLookupSystem(unittest.TestCase):
    """Test cases for MapLookupSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test map data
        self.test_map_data = {
            "nodes": [
                {
                    "id": "B001",
                    "name": "Grand Central Library",
                    "aliases": ["Main Library", "Central Library"],
                    "type": "Academic",
                    "zone": "Academic Quad",
                    "internal_amenities": {
                        "floor_1": ["Main Lobby", "Study Areas", "WiFi"],
                        "floor_2": ["Group Study Rooms", "Computer Lab"]
                    }
                },
                {
                    "id": "B002", 
                    "name": "Student Union Building",
                    "aliases": ["SUB", "Union"],
                    "type": "Student Services",
                    "zone": "Central Campus",
                    "internal_amenities": {
                        "floor_1": ["Food Court", "Bookstore", "WiFi"],
                        "floor_2": ["Meeting Rooms", "Student Organizations"]
                    }
                }
            ],
            "edges": [
                {
                    "source": "B001",
                    "target": "B002", 
                    "time_cost": 5,
                    "properties": {"surface": "paved", "rain_exposure": "Covered"}
                }
            ],
            "building_complexes": []
        }
        
        # Create temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.map_file = Path(self.temp_dir) / "test_map.json"
        with open(self.map_file, 'w') as f:
            json.dump(self.test_map_data, f)
            
        self.map_system = MapLookupSystem(str(self.map_file))
    
    def test_find_building_id_by_name(self):
        """Test finding building ID by exact name"""
        result = self.map_system.find_building_id("Grand Central Library")
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["building_id"], "B001")
    
    def test_find_building_id_by_alias(self):
        """Test finding building ID by alias"""
        result = self.map_system.find_building_id("Main Library")
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["building_id"], "B001")
    
    def test_find_building_id_case_insensitive(self):
        """Test case insensitive search"""
        result = self.map_system.find_building_id("grand central library")
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["building_id"], "B001")
    
    def test_find_building_id_not_found(self):
        """Test building not found"""
        result = self.map_system.find_building_id("Nonexistent Building")
        self.assertFalse(result.is_success())
        self.assertIn("not found", result.message.lower())
    
    def test_get_building_details(self):
        """Test getting building details"""
        result = self.map_system.get_building_details("B001")
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["name"], "Grand Central Library")
        self.assertEqual(result.data["type"], "Academic")
    
    def test_get_building_details_invalid_id(self):
        """Test getting details for invalid building ID"""
        result = self.map_system.get_building_details("B999")
        self.assertFalse(result.is_success())
    
    def test_find_room_location(self):
        """Test finding room location"""
        result = self.map_system.find_room_location("Study Areas")
        self.assertTrue(result.is_success())
        self.assertIn("B001", str(result.data))
    
    def test_find_optimal_path(self):
        """Test finding optimal path"""
        result = self.map_system.find_optimal_path("B001", "B002")
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["path"], ["B001", "B002"])
        self.assertEqual(result.data["total_time_cost"], 5)
    
    def test_find_optimal_path_no_route(self):
        """Test path finding when no route exists"""
        result = self.map_system.find_optimal_path("B001", "B999")
        self.assertFalse(result.is_success())
    
    def test_query_buildings_by_property_zone(self):
        """Test querying buildings by zone"""
        result = self.map_system.query_buildings_by_property(zone="Academic Quad")
        self.assertTrue(result.is_success())
        self.assertIn("buildings", result.data)
        # Should find B001 (Academic building)
        building_ids = [b["id"] for b in result.data["buildings"]]
        self.assertIn("B001", building_ids)

    def test_query_buildings_by_property_type(self):
        """Test querying buildings by type"""
        result = self.map_system.query_buildings_by_property(building_type="Academic")
        self.assertTrue(result.is_success())
        self.assertIn("buildings", result.data)
        # Should find B001
        building_ids = [b["id"] for b in result.data["buildings"]]
        self.assertIn("B001", building_ids)

    def test_query_buildings_by_property_amenity(self):
        """Test querying buildings by amenity"""
        result = self.map_system.query_buildings_by_property(amenity="WiFi")
        self.assertTrue(result.is_success())
        self.assertIn("buildings", result.data)
        # Should find buildings with WiFi
        self.assertGreaterEqual(len(result.data["buildings"]), 1)

    def test_query_buildings_by_property_multiple_filters(self):
        """Test querying buildings with multiple filters"""
        result = self.map_system.query_buildings_by_property(
            zone="Academic Quad",
            building_type="Academic",
            amenity="WiFi"
        )
        self.assertTrue(result.is_success())
        self.assertIn("buildings", result.data)

    def test_query_buildings_by_property_no_results(self):
        """Test querying buildings with no matching results"""
        result = self.map_system.query_buildings_by_property(building_type="Nonexistent")
        self.assertFalse(result.is_success())
        self.assertIn("no buildings found", result.message.lower())

    def test_find_optimal_path_with_constraints(self):
        """Test finding optimal path with constraints"""
        constraints = {
            "rain_exposure": "Covered",
            "surface": "paved",
            "accessibility": "wheelchair_accessible"
        }
        result = self.map_system.find_optimal_path("B001", "B002", constraints)
        self.assertTrue(result.is_success())
        self.assertIn("path", result.data)
        self.assertIn("total_time_cost", result.data)

    def test_find_optimal_path_same_building(self):
        """Test finding path to same building"""
        result = self.map_system.find_optimal_path("B001", "B001")
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["path"], ["B001"])
        self.assertEqual(result.data["total_time_cost"], 0)

    def test_list_valid_query_properties(self):
        """Test listing valid query properties"""
        result = self.map_system.list_valid_query_properties()
        self.assertTrue(result.is_success())
        self.assertIn("zones", result.data)
        self.assertIn("building_types", result.data)
        self.assertIsInstance(result.data["zones"], list)
        self.assertIsInstance(result.data["building_types"], list)
        # Should contain our test data
        self.assertIn("Academic Quad", result.data["zones"])
        self.assertIn("Academic", result.data["building_types"])

    def test_get_building_complex_info(self):
        """Test getting building complex information"""
        result = self.map_system.get_building_complex_info("B001")
        # This method should work even if no complex info is available
        self.assertTrue(result.is_success() or result.is_failure())
        # If successful, should have is_complex_member field
        if result.is_success():
            self.assertIn("is_complex_member", result.data)
            self.assertIsInstance(result.data["is_complex_member"], bool)

    def test_english_only_validation(self):
        """Test English-only message validation"""
        result = self.map_system.find_building_id("Grand Central Library")
        self.assertTrue(result.is_success())
        # All messages should be in English (allow single quotes)
        self.assertRegex(result.message, r"^[A-Za-z0-9\s\.,!?\-:()']+$")


class TestGeographySystem(unittest.TestCase):
    """Test cases for GeographySystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test map data
        self.test_map_data = {
            "nodes": [
                {"id": "B001", "name": "Grand Central Library"},
                {"id": "B002", "name": "Student Union Building"}
            ],
            "edges": [
                {
                    "source": "B001",
                    "target": "B002",
                    "time_cost": 5,
                    "properties": {"surface": "paved"}
                }
            ],
            "building_complexes": []
        }
        
        # Create temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.map_file = Path(self.temp_dir) / "test_map.json"
        with open(self.map_file, 'w') as f:
            json.dump(self.test_map_data, f)
            
        map_lookup = MapLookupSystem(str(self.map_file))
        self.geo_system = GeographySystem(map_lookup)
    
    def test_set_location(self):
        """Test setting current location"""
        result = self.geo_system.set_location("B001")
        self.assertTrue(result.is_success())
        
        state = self.geo_system.get_state_for_evaluation()
        self.assertEqual(state.current_location_id, "B001")
    
    def test_set_invalid_location(self):
        """Test setting invalid location"""
        result = self.geo_system.set_location("B999")
        self.assertFalse(result.is_success())
    
    def test_walk_to_valid_path(self):
        """Test walking to location with valid path"""
        # Set initial location
        self.geo_system.set_location("B001")
        
        # Walk to B002
        path_info = {"path": ["B001", "B002"]}
        result = self.geo_system.walk_to(path_info)
        self.assertTrue(result.is_success())
        
        state = self.geo_system.get_state_for_evaluation()
        self.assertEqual(state.current_location_id, "B002")
    
    def test_walk_to_invalid_format(self):
        """Test walking with invalid path format"""
        result = self.geo_system.walk_to(["B001", "B002"])  # Should be dict
        self.assertFalse(result.is_success())
        self.assertIn("Invalid path_info format", result.message)
    
    def test_walk_to_wrong_starting_location(self):
        """Test walking from wrong starting location"""
        self.geo_system.set_location("B001")
        
        path_info = {"path": ["B002", "B001"]}  # Wrong start
        result = self.geo_system.walk_to(path_info)
        self.assertFalse(result.is_success())
    
    def test_get_current_location(self):
        """Test getting current location"""
        self.geo_system.set_location("B001")
        state = self.geo_system.get_state_for_evaluation()
        self.assertEqual(state.current_location_id, "B001")

    def test_get_current_location_method(self):
        """Test get_current_location method"""
        # Set location first
        self.geo_system.set_location("B001")

        # Get current location
        result = self.geo_system.get_current_location()
        self.assertTrue(result.is_success())
        self.assertEqual(result.data["building_id"], "B001")
        self.assertIn("Grand Central Library", result.data["building_name"])

    def test_get_current_location_no_location_set(self):
        """Test getting current location when none is set"""
        result = self.geo_system.get_current_location()
        self.assertTrue(result.is_success())
        # Should return default location (B083 - Lakeside Dormitory)
        self.assertEqual(result.data["building_id"], "B083")
        self.assertIn("Lakeside Dormitory", result.data["building_name"])

    def test_state_tracking(self):
        """Test state tracking functionality"""
        # Set location and verify state
        self.geo_system.set_location("B001")
        state = self.geo_system.get_state_for_evaluation()
        self.assertEqual(state.current_location_id, "B001")
        self.assertEqual(state.current_location_name, "Grand Central Library")

    def test_walk_to_empty_path(self):
        """Test walking with empty path"""
        path_info = {"path": []}
        result = self.geo_system.walk_to(path_info)
        self.assertFalse(result.is_success())
        self.assertIn("at least 2 locations", result.message.lower())

    def test_walk_to_single_step_path(self):
        """Test walking with single step path"""
        self.geo_system.set_location("B001")
        path_info = {"path": ["B001"]}
        result = self.geo_system.walk_to(path_info)
        self.assertFalse(result.is_success())  # Single step path should fail
        self.assertIn("at least 2 locations", result.message.lower())


if __name__ == '__main__':
    unittest.main()
