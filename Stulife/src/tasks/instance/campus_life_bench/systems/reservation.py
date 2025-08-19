"""
Reservation System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..tools import ToolResult, ensure_english_message
from .map_and_geography import MapLookupSystem
from .information import InformationSystem


@dataclass
class ReservationRecord:
    """Represents a reservation record"""
    location_id: str
    area: str
    item_name: str
    seat_id: Optional[str]
    date: str
    time_slot: str
    booking_task_id: str


class ReservationSystem:
    """
    Intelligent reservation system with dynamic availability generation
    Supports both facility and seat reservations with global state persistence
    """
    
    def __init__(self, map_lookup_system: MapLookupSystem, information_system: InformationSystem):
        """
        Initialize reservation system
        
        Args:
            map_lookup_system: Reference to map lookup system for building data
            information_system: Reference to information system for campus data
        """
        self.map_lookup_system = map_lookup_system
        self.information_system = information_system
        self._campus_data = self.information_system.get_campus_data() or {}
        
        # Global persistent reservations
        self._global_reservations: List[ReservationRecord] = []
        
        # Current task context (set by CampusTask)
        self._current_task_context: Optional[Dict[str, Any]] = None

        # Configured availability from world_state_change
        self._configured_availability: Dict[str, Any] = {}
    
    def set_availability(self, parameters: Dict[str, Any]) -> None:
        """
        Set pre-configured availability for a location/item.
        Called by CampusEnvironment based on world_state_change.
        
        Args:
            parameters: Availability parameters from task data.
        """
        item_name = parameters.get("item_name")
        building_id = parameters.get("building_id")
        available_times = parameters.get("available_times", [])
        
        if item_name and building_id:
            key = (building_id, item_name)
            self._configured_availability[key] = available_times
            print(f"Set pre-configured availability for {item_name} in {building_id}: {available_times}")
    
    def set_task_context(self, task_data: Dict[str, Any]) -> None:
        """
        Set current task context for intelligent availability generation
        Called by CampusTask before task execution
        
        Args:
            task_data: Current task data including ground truth and constraints
        """
        self._current_task_context = task_data
    
    def query_availability(self, location_id: str, date: str) -> ToolResult:
        """
        Query availability for a location on a specific date
        Uses intelligent availability generation based on current task context
        
        Args:
            location_id: Building ID to query
            date: Date to query (e.g., "Week 4, Saturday")
            
        Returns:
            ToolResult with availability information
        """
        try:
            if not all([location_id, date]):
                return ToolResult.failure("Both location_id and date are required.")

            # Get building details
            building_result = self.map_lookup_system.get_building_details(location_id)
            if not building_result.is_success():
                return ToolResult.failure(f"Building '{location_id}' not found.")
            
            building_data = building_result.data
            if not isinstance(building_data, dict):
                return ToolResult.failure(f"Retrieved data for building '{location_id}' is not in the expected format.")
            
            building_name = building_data.get("name", location_id)

            # Decide generation strategy based on ground_truth
            availability = {}
            use_deterministic_seats = False
            if self._current_task_context:
                ground_truth = self._current_task_context.get("ground_truth", {})
                if isinstance(ground_truth, dict) and "seat_id" in ground_truth:
                    use_deterministic_seats = True

            if use_deterministic_seats:
                # For seat-specific tasks, generate a detailed puzzle
                availability = self._generate_deterministic_availability(building_data, date)
            else:
                # For all other tasks, generate random hierarchical availability
                availability = self._generate_random_hierarchical_availability(building_data, date)
            
            # Format availability message with hierarchy
            message = f"Availability query successful! {building_name} on {date}:"
            
            for time_slot, floors in availability.items():
                if not floors: continue
                message += f"\n- Time slot {time_slot}:"
                # Handle both formats: with and without floor keys
                if any(key.startswith("floor_") for key in floors.keys()):
                    # Format with floors
                    for floor, facilities in floors.items():
                        message += f"\n  - {floor}:"
                        for facility_name, facility_info in facilities.items():
                            message += f"\n    - Facility: {facility_name}"
                            if "seats" in facility_info and facility_info["seats"]:
                                for seat in facility_info["seats"]:
                                    if isinstance(seat, dict) and seat.get("status") != "booked":
                                        features_str = ", ".join(seat.get("features", []))
                                        message += f"\n      - Available seat: {seat.get('seat_id', 'Unknown ID')} with features: [{features_str}]"
                            else:
                                message += " (Available)"
                else:
                    # Format without floors (for deterministic results)
                    for facility_name, facility_info in floors.items():
                        message += f"\n  - Facility: {facility_name}"
                        if "seats" in facility_info and facility_info["seats"]:
                            for seat in facility_info["seats"]:
                                if isinstance(seat, dict) and seat.get("status") != "booked":
                                    features_str = ", ".join(seat.get("features", []))
                                    message += f"\n    - Available seat: {seat.get('seat_id', 'Unknown ID')} with features: [{features_str}]"
                        else:
                            message += " (Available)"
            
            return ToolResult.success(ensure_english_message(message), {
                "location_id": location_id,
                "building_name": building_name,
                "date": date,
                "availability": availability
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to query availability: {str(e)}")
    
    def _is_target_location(self, location_id: str, date: str, building_data: Optional[Dict[str, Any]]) -> bool:
        """
        Check if this is the target location for current task
        
        Args:
            location_id: Building ID to check
            date: Date to check
            building_data: Pre-fetched building data dictionary
            
        Returns:
            True if this is the target location and date
        """
        if not self._current_task_context or not isinstance(building_data, dict):
            return False
        
        details = self._current_task_context.get("details", {})
        target_library = details.get("target_library")
        target_date = self._current_task_context.get("target_date")
        
        # Check if location matches target
        if target_library:
            building_name = building_data.get("name")
            if building_name == target_library and date == target_date:
                return True
        
        return False
    
    def _generate_deterministic_availability(self, building_data: Dict[str, Any], date: str) -> Dict[str, Dict[str, Any]]:
        """
        Generate availability for a seat-specific task using real data from campus_data.json,
        with intelligent distractor generation.
        
        Args:
            building_data: Building information (used to get the building ID)
            date: Date for availability
            
        Returns:
            Hierarchical availability dictionary with real seat data and distractors.
        """
        if not self._current_task_context:
            return {}

        availability = {}
        details = self._current_task_context.get("details", {})
        ground_truth = self._current_task_context.get("ground_truth", {})
        
        # 1. Get task parameters
        location_id = building_data.get("id")
        if not location_id:
            return {}
            
        target_item_name = ground_truth.get("item_name", "Study Area")
        required_features = set(details.get("implied_requirements", []))
        task_time = details.get("task_time", "16:30")
        duration_hours = details.get("reservation_duration_hours", 1.5)
        target_time_slot = self._calculate_time_slot(task_time, duration_hours)

        # 2. Find the correct building and room to extract all real seats
        all_real_seats_in_room = []
        detailed_building_data = next((lib for lib in self._campus_data.get("library_seats", {}).get("libraries", []) if lib.get("id") == location_id), None)
        
        if not detailed_building_data:
            print(f"DEBUG: No library data found for building_id '{location_id}'")
            return self._generate_fallback_availability(target_time_slot, target_item_name)

        # Find the specific room in the detailed data
        target_room_data = None
        for floor, rooms in detailed_building_data.get("internal_amenities", {}).items():
            for room in rooms:
                if isinstance(room, dict) and room.get("room_name") == target_item_name:
                    target_room_data = room
                    break
            if target_room_data:
                break
        
        if target_room_data:
            all_real_seats_in_room.extend(target_room_data.get("seats", []))

        if not all_real_seats_in_room:
            print(f"DEBUG: No real seats found for {target_item_name} in {location_id}")
            return self._generate_fallback_availability(target_time_slot, target_item_name)

        # 3. Separate seats into correct and distractor piles
        correct_seats = []
        distractor_seats = []
        for seat in all_real_seats_in_room:
            seat_features = set(seat.get("features", []))
            if required_features.issubset(seat_features):
                correct_seats.append(seat)
            else:
                distractor_seats.append(seat)
        
        # 4. Build the availability for the target time slot
        seats_for_target_slot = correct_seats.copy()
        # Add a number of distractors to meet the desired count, up to a max of 10 total seats
        num_distractors_to_add = min(len(distractor_seats), 10 - len(seats_for_target_slot))
        if num_distractors_to_add > 0:
            seats_for_target_slot.extend(random.sample(distractor_seats, k=num_distractors_to_add))
        
        random.shuffle(seats_for_target_slot)
        availability[target_time_slot] = {
            target_item_name: {"seats": seats_for_target_slot}
        }
        
        # 5. Generate availability for other time slots using only distractors or a subset of real seats
        other_slots = ["09:00-10:30", "10:30-12:00", "14:00-15:30"]
        if target_time_slot in other_slots:
            other_slots.remove(target_time_slot)
        
        for slot in other_slots:
            num_other_seats = min(len(all_real_seats_in_room), 5)
            other_seats_sample = random.sample(all_real_seats_in_room, k=num_other_seats)
            availability[slot] = {
                target_item_name: {"seats": other_seats_sample}
            }
            
        return availability

    def _generate_fallback_availability(self, time_slot: str, item_name: str) -> Dict[str, Any]:
        """Generates minimal fallback availability when real data isn't found."""
        return {
            time_slot: {
                item_name: {"seats": []}
            }
        }

    def _generate_random_hierarchical_availability(self, building_data: Dict[str, Any], date: str) -> Dict[str, Dict[str, Any]]:
        """
        Generate hierarchical availability using real data for non-seat-specific tasks.
        Args:
            building_data: Building information
            date: Date for availability
        Returns:
            Hierarchical availability dictionary
        """
        availability = {}
        time_slots = ["09:00-10:30", "10:30-12:00", "14:00-15:30", "15:30-17:00", "16:30-18:00"]
        
        # 1. Get building amenities from the primary building_data which is from map_v1.5.json
        amenities_from_map = building_data.get("internal_amenities", {})
        if not amenities_from_map or not isinstance(amenities_from_map, dict):
            return {}

        # 2. Find the corresponding detailed building data from campus_data
        location_id = building_data.get("id")
        detailed_building_data = next((lib for lib in self._campus_data.get("library_seats", {}).get("libraries", []) if lib.get("id") == location_id), None)

        if not detailed_building_data:
            return {} # Cannot generate availability without detailed seat info

        # 3. Create a lookup for detailed room info
        room_details_lookup = {}
        for floor, rooms in detailed_building_data.get("internal_amenities", {}).items():
            for room in rooms:
                if isinstance(room, dict) and "room_name" in room:
                    room_details_lookup[room["room_name"]] = room

        # 4. Generate availability for each time slot based on map structure
        for slot in time_slots:
            availability[slot] = {}
            # Iterate through floors and rooms from the map data
            for floor, room_names in amenities_from_map.items():
                floor_amenities = {}
                for room_name in room_names:
                    # Look up detailed info in campus_data
                    detailed_room = room_details_lookup.get(room_name)
                    
                    if detailed_room:
                        seats = detailed_room.get("seats", [])
                        # Limit the number of seats shown to 10
                        seats_to_show = random.sample(seats, k=min(len(seats), 10))
                        floor_amenities[room_name] = {
                            "seats": seats_to_show,
                            "features": detailed_room.get("features", [])
                        }
                    else:
                        # If no detailed info, mark as available without seats
                        floor_amenities[room_name] = {"seats": []}
                
                if floor_amenities:
                    if floor not in availability[slot]:
                        availability[slot][floor] = {}
                    availability[slot][floor].update(floor_amenities)
                        
        return availability
    
    def _calculate_time_slot(self, start_time: str, duration_hours: float) -> str:
        """
        Calculate time slot from start time and duration
        
        Args:
            start_time: Start time (e.g., "16:30")
            duration_hours: Duration in hours
            
        Returns:
            Time slot string (e.g., "16:30-18:00")
        """
        try:
            hour, minute = map(int, start_time.split(":"))
            start_minutes = hour * 60 + minute
            end_minutes = start_minutes + int(duration_hours * 60)
            
            end_hour = end_minutes // 60
            end_minute = end_minutes % 60
            
            return f"{start_time}-{end_hour:02d}:{end_minute:02d}"
        except:
            return f"{start_time}-{start_time}"  # Fallback
    
    def make_booking(self, location_id: str, item_name: str, date: str, time_slot: str, seat_id: Optional[str] = None) -> ToolResult:
        """
        Make a booking for a location/seat
        
        Args:
            location_id: Building ID
            item_name: Name of facility or room to book
            date: Date for booking
            time_slot: Time slot for booking
            seat_id: Optional seat ID for seat bookings
            
        Returns:
            ToolResult indicating booking success or failure
        """
        try:
            if not all([location_id, item_name, date, time_slot]):
                return ToolResult.failure("Location ID, item name, date, and time slot are all required.")
            
            # Check for conflicts with existing reservations
            for reservation in self._global_reservations:
                if (reservation.location_id == location_id and
                    reservation.date == date and
                    self._time_slots_overlap(reservation.time_slot, time_slot)):
                    
                    if ((seat_id and reservation.seat_id == seat_id) or
                        (not seat_id and reservation.item_name == item_name)):
                        return ToolResult.failure(f"The requested {item_name} is already booked for the specified time slot.")
            
            # Create reservation record
            task_id = self._current_task_context.get("task_id", "unknown") if self._current_task_context else "unknown"
            
            reservation = ReservationRecord(
                location_id=location_id,
                area="floor_1",  # Default area
                item_name=item_name,
                seat_id=seat_id,
                date=date,
                time_slot=time_slot,
                booking_task_id=task_id
            )
            
            # Add to global reservations
            self._global_reservations.append(reservation)
            
            # Generate success message
            if seat_id:
                message = f"Booking successful! You have successfully reserved seat {seat_id} in {item_name} for {date} from {time_slot}."
            else:
                message = f"Booking successful! You have successfully reserved {item_name} for {date} from {time_slot}."
            
            return ToolResult.success(ensure_english_message(message), {
                "reservation_id": len(self._global_reservations),
                "location_id": location_id,
                "item_name": item_name,
                "seat_id": seat_id,
                "date": date,
                "time_slot": time_slot
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to make booking: {str(e)}")
    
    def _time_slots_overlap(self, slot1: str, slot2: str) -> bool:
        """
        Check if two time slots overlap
        
        Args:
            slot1: First time slot (e.g., "14:00-16:00")
            slot2: Second time slot
            
        Returns:
            True if slots overlap
        """
        try:
            def parse_time_slot(slot):
                start_str, end_str = slot.split("-")
                start_hour, start_min = map(int, start_str.split(":"))
                end_hour, end_min = map(int, end_str.split(":"))
                return start_hour * 60 + start_min, end_hour * 60 + end_min
            
            start1, end1 = parse_time_slot(slot1)
            start2, end2 = parse_time_slot(slot2)
            
            return not (end1 <= start2 or end2 <= start1)
        except:
            return False  # If parsing fails, assume no overlap
    
    def get_reservations_for_evaluation(self, task_id: str) -> List[ReservationRecord]:
        """
        Get reservations made by a specific task for evaluation
        Used by CampusTask during evaluation
        
        Args:
            task_id: Task ID to filter by
            
        Returns:
            List of ReservationRecord objects for the task
        """
        return [r for r in self._global_reservations if r.booking_task_id == task_id]
    
    def get_all_reservations(self) -> List[ReservationRecord]:
        """
        Get all reservations for debugging/testing
        
        Returns:
            List of all ReservationRecord objects
        """
        return self._global_reservations.copy()
