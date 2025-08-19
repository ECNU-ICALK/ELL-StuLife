"""
CampusEnvironment - Core environment class for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from .tools import ToolResult, ensure_english_message
from .systems import (
    WorldTimeSystem, CalendarSystem, MapLookupSystem, GeographySystem,
    ReservationSystem, InformationSystem, CourseSelectionSystem, EmailSystem
)


class CampusEnvironment:
    """
    Core environment class that maintains all campus simulation state
    and provides unified tool interface for Agent interaction.
    
    This class serves as the single source of truth for all campus state
    and delegates tool calls to appropriate subsystems.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the campus environment with all subsystems

        Args:
            data_dir: Directory containing campus data files
        """
        # Set up data directory
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = Path(data_dir)

        # Check for background directory structure
        self.background_dir = self.data_dir / "background"
        if not self.background_dir.exists():
            # Fallback to data_dir for backward compatibility
            self.background_dir = self.data_dir
            print(f"⚠️  Background directory not found, using fallback: {self.background_dir}")
        else:
            print(f"✅ Using background directory: {self.background_dir}")

        # Initialize all subsystems
        self._initialize_subsystems()

        # Track current day for daily reset functionality
        self._current_day: Optional[str] = None
    
    def _initialize_subsystems(self):
        """Initialize all campus subsystems"""
        # World Time System (no tools, logic handled by CampusTask)
        self.world_time_system = WorldTimeSystem()

        # Calendar System
        self.calendar_system = CalendarSystem()

        # Map and Geography Systems
        map_data_path = self.background_dir / "map_v1.5.json"
        self.map_lookup_system = MapLookupSystem(map_data_path)
        self.geography_system = GeographySystem(self.map_lookup_system)

        # Information System - use background directory
        bibliography_path = self.background_dir / "bibliography.json"
        data_system_path = self.background_dir / "campus_data.json"
        self.information_system = InformationSystem(bibliography_path, data_system_path)

        # Reservation System
        self.reservation_system = ReservationSystem(
            map_lookup_system=self.map_lookup_system,
            information_system=self.information_system
        )

        # Course Selection System
        courses_path = self.background_dir / "courses.json"
        self.course_selection_system = CourseSelectionSystem(courses_path)

        # Email System
        self.email_system = EmailSystem()
    
    def daily_reset(self, new_day: str) -> None:
        """
        Perform daily reset operations
        Called by CampusTask when a new simulation day begins
        
        Args:
            new_day: The new simulation day (e.g., "Week 2, Saturday")
        """
        self._current_day = new_day
        
        # Reset geography to dormitory
        self.geography_system.daily_reset()
        
        # Other systems may need daily reset in the future
        # self.calendar_system.daily_reset()
        # self.reservation_system.daily_reset()
    
    def set_initial_location(self, building_id: str) -> ToolResult:
        """
        Set agent's initial location for a task
        Called by CampusTask when source_building_id is specified
        
        Args:
            building_id: The building ID to set as current location
            
        Returns:
            ToolResult indicating success or failure
        """
        return self.geography_system.set_location(building_id)
    
    def get_current_location_for_validation(self) -> str:
        """
        Get current location ID for require_place validation
        Used by CampusTask for prerequisite checking
        
        Returns:
            Current building ID
        """
        result = self.geography_system.get_current_location()
        if result.is_success() and result.data:
            return result.data.get("building_id", "")
        return ""
    
    def apply_world_state_changes(self, changes: List[Dict[str, Any]]) -> None:
        """
        Apply world state changes before task execution
        Called by CampusTask during _reset
        
        Args:
            changes: List of world state change objects
        """
        for change in changes:
            change_type = change.get("change_type")
            system = change.get("system")
            action = change.get("action")

            if change_type == "popularity_update":
                course_code = change.get("course_code")
                new_value = change.get("new_value")
                self.course_selection_system.update_course_popularity(course_code, new_value)

            elif change_type == "seats_left_update":
                course_code = change.get("course_code")
                new_value = change.get("new_value")
                self.course_selection_system.update_course_seats(course_code, new_value)

            elif change_type == "advisor_availability_set":
                advisor_id = change.get("advisor_id")
                date = change.get("date")
                available_slots = change.get("available_slots", [])
                if advisor_id and date and available_slots:
                    self.calendar_system.set_advisor_availability(advisor_id, date, available_slots)
            
            elif system == "reservation" and action == "set_availability":
                parameters = change.get("parameters", {})
                if parameters:
                    self.reservation_system.set_availability(parameters)
    
    # ========== Calendar System Tools ==========
    
    def add_event(self, calendar_id: str, event_title: str, location: str, time: str, description: Optional[str] = None) -> ToolResult:
        """Add an event to the specified calendar"""
        return self.calendar_system.add_event(calendar_id, event_title, location, time, description)
    
    def remove_event(self, calendar_id: str, event_id: str) -> ToolResult:
        """Remove an event from the specified calendar"""
        return self.calendar_system.remove_event(calendar_id, event_id)
    
    def update_event(self, calendar_id: str, event_id: str, new_details: Dict[str, Any]) -> ToolResult:
        """Update an event in the specified calendar"""
        return self.calendar_system.update_event(calendar_id, event_id, new_details)
    
    def view_schedule(self, calendar_id: str, date: str) -> ToolResult:
        """View schedule for the specified calendar and date"""
        return self.calendar_system.view_schedule(calendar_id, date)
    
    def query_advisor_availability(self, advisor_id: str, date: str) -> ToolResult:
        """Query advisor availability for the specified date"""
        return self.calendar_system.query_advisor_availability(advisor_id, date)
    
    # ========== Map Lookup System Tools ==========
    
    def find_building_id(self, building_name: str) -> ToolResult:
        """Find building ID by name or alias"""
        return self.map_lookup_system.find_building_id(building_name)
    
    def get_building_details(self, building_id: str) -> ToolResult:
        """Get detailed information about a building"""
        return self.map_lookup_system.get_building_details(building_id)
    
    def find_room_location(self, room_query: str, building_id: Optional[str] = None, zone: Optional[str] = None) -> ToolResult:
        """Find room location within campus or specified area"""
        return self.map_lookup_system.find_room_location(room_query, building_id, zone)
    
    def find_optimal_path(self, source_building_id: str, target_building_id: str, constraints: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Find optimal path between two buildings"""
        return self.map_lookup_system.find_optimal_path(source_building_id, target_building_id, constraints)
    
    def query_buildings_by_property(self, zone: Optional[str] = None, building_type: Optional[str] = None, amenity: Optional[str] = None) -> ToolResult:
        """Query buildings by properties"""
        return self.map_lookup_system.query_buildings_by_property(zone, building_type, amenity)
    
    def get_building_complex_info(self, building_id: str) -> ToolResult:
        """Get building complex information"""
        return self.map_lookup_system.get_building_complex_info(building_id)
    
    def list_valid_query_properties(self) -> ToolResult:
        """List all valid query properties"""
        return self.map_lookup_system.list_valid_query_properties()
    
    # ========== Geography System Tools ==========
    
    def walk_to(self, path_info: Dict[str, Any]) -> ToolResult:
        """Walk to a location using path information"""
        return self.geography_system.walk_to(path_info)
    
    def get_current_location(self) -> ToolResult:
        """Get current location"""
        return self.geography_system.get_current_location()
    
    # ========== Reservation System Tools ==========
    
    def query_availability(self, location_id: str, date: str) -> ToolResult:
        """Query availability for a location on a specific date"""
        return self.reservation_system.query_availability(location_id, date)
    
    def make_booking(self, location_id: str, item_name: str, date: str, time_slot: str, seat_id: Optional[str] = None) -> ToolResult:
        """Make a booking for a location/seat"""
        return self.reservation_system.make_booking(location_id, item_name, date, time_slot, seat_id)
    
    # ========== Information System Tools ==========
    
    def list_chapters(self, book_title: str) -> ToolResult:
        """List chapters in a book"""
        return self.information_system.list_chapters(book_title)
    
    def list_sections(self, book_title: str, chapter_title: str) -> ToolResult:
        """List sections in a chapter"""
        return self.information_system.list_sections(book_title, chapter_title)
    
    def list_articles(self, book_title: str, chapter_title: str, section_title: str) -> ToolResult:
        """List articles in a section"""
        return self.information_system.list_articles(book_title, chapter_title, section_title)
    
    def view_article(self, identifier: str, by: str) -> ToolResult:
        """View an article by title or ID"""
        return self.information_system.view_article(identifier, by)
    
    def list_by_category(self, category: str, entity_type: str, level: Optional[str] = None) -> ToolResult:
        """List entities by category"""
        return self.information_system.list_by_category(category, entity_type, level)
    
    def query_by_identifier(self, identifier: str, by: str, entity_type: str) -> ToolResult:
        """Query entity by identifier"""
        return self.information_system.query_by_identifier(identifier, by, entity_type)
    
    def list_books_by_category(self, category: str) -> ToolResult:
        """List library books by category"""
        return self.information_system.list_books_by_category(category)
    
    def search_books(self, query: str, search_type: str = "title") -> ToolResult:
        """Search library books by title or author"""
        return self.information_system.search_books(query, search_type)
    
    # ========== Course Selection System Tools ==========
    
    def browse_courses(self, filters: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Browse available courses with optional filters"""
        return self.course_selection_system.browse_courses(filters)
    
    def add_course(self, section_id: str) -> ToolResult:
        """Add a course to draft schedule"""
        return self.course_selection_system.add_course(section_id)
    
    def remove_course(self, section_id: str) -> ToolResult:
        """Remove a course from draft schedule"""
        return self.course_selection_system.remove_course(section_id)
    
    def assign_pass(self, section_id: str, pass_type: str) -> ToolResult:
        """Assign a pass type to a course"""
        return self.course_selection_system.assign_pass(section_id, pass_type)
    
    def view_draft(self) -> ToolResult:
        """View current draft schedule"""
        return self.course_selection_system.view_draft()
    
    def submit_draft(self) -> ToolResult:
        """Submit draft schedule for final registration"""
        return self.course_selection_system.submit_draft()
    
    # ========== Email System Tools ==========
    
    def send_email(self, recipient: str, subject: str, body: str) -> ToolResult:
        """Send an email"""
        return self.email_system.send_email(recipient, subject, body)

    def get_and_clear_self_schedule_changes(self) -> List[Dict[str, Any]]:
        """Get calendar changes and clear the log"""
        return self.calendar_system.get_and_clear_self_schedule_changes()
