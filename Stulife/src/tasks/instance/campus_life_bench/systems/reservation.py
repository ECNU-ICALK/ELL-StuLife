"""
Reservation System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..tools import ToolResult, ensure_english_message
from .map_and_geography import MapLookupSystem


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
    
    def __init__(self, map_lookup_system: MapLookupSystem):
        """
        Initialize reservation system
        
        Args:
            map_lookup_system: Reference to map lookup system for building data
        """
        self.map_lookup_system = map_lookup_system
        
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

            # Check for pre-configured availability first
            for (building_id, item_name), available_times in self._configured_availability.items():
                if building_id == location_id:
                    # Filter times by the requested date
                    relevant_times = [t for t in available_times if date in t]
                    if relevant_times:
                        building_result = self.map_lookup_system.get_building_details(location_id)
                        building_name = building_result.data["name"] if building_result.is_success() else location_id
                        
                        message = f"Availability query successful! {building_name} on {date}:"
                        availability = {}
                        
                        # Assuming pre-configured times are for specific items
                        for time_slot in relevant_times:
                            message += f"\n- Time slot {time_slot}:\n  - Available facility: {item_name}"
                            if time_slot not in availability:
                                availability[time_slot] = []
                            availability[time_slot].append({"item_name": item_name})
                        
                        return ToolResult.success(ensure_english_message(message), {
                            "location_id": location_id,
                            "building_name": building_name,
                            "date": date,
                            "availability": availability
                        })
            
            # Get building details
            building_result = self.map_lookup_system.get_building_details(location_id)
            if not building_result.is_success():
                return ToolResult.failure(f"Building '{location_id}' not found.")
            
            building_data = building_result.data
            
            # Check if this is the target location for current task
            is_target_location = self._is_target_location(location_id, date)
            
            if is_target_location:
                # Generate deterministic availability for target location
                availability = self._generate_deterministic_availability(building_data, date)
            else:
                # Generate random availability for non-target locations
                availability = self._generate_random_availability(building_data, date)
            
            # Format availability message
            message = f"Availability query successful! {building_data['name']} on {date}:"
            
            for time_slot, items in availability.items():
                if items:
                    message += f"\n- Time slot {time_slot}:"
                    for item in items:
                        if "seat_id" in item:
                            message += f"\n  - Available seat: {item['seat_id']}"
                        else:
                            message += f"\n  - Available facility: {item['item_name']}"
            
            return ToolResult.success(ensure_english_message(message), {
                "location_id": location_id,
                "building_name": building_data["name"],
                "date": date,
                "availability": availability
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to query availability: {str(e)}")
    
    def _is_target_location(self, location_id: str, date: str) -> bool:
        """
        Check if this is the target location for current task
        
        Args:
            location_id: Building ID to check
            date: Date to check
            
        Returns:
            True if this is the target location and date
        """
        if not self._current_task_context:
            return False
        
        details = self._current_task_context.get("details", {})
        target_library = details.get("target_library")
        target_date = self._current_task_context.get("target_date")
        
        # Check if location matches target
        if target_library:
            # Get building name for comparison
            building_result = self.map_lookup_system.get_building_details(location_id)
            if building_result.is_success():
                building_name = building_result.data["name"]
                if building_name == target_library and date == target_date:
                    return True
        
        return False
    
    def _generate_deterministic_availability(self, building_data: Dict[str, Any], date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate deterministic availability for target location
        Creates a puzzle where only ground truth satisfies all constraints
        
        Args:
            building_data: Building information
            date: Date for availability
            
        Returns:
            Dictionary mapping time slots to available items
        """
        if not self._current_task_context:
            return {}
        
        details = self._current_task_context.get("details", {})
        ground_truth = self._current_task_context.get("ground_truth", [])
        
        # Extract task parameters
        task_time = details.get("task_time", "16:30")
        duration_hours = details.get("reservation_duration_hours", 1.5)
        constraints = details.get("implied_requirements", [])
        
        # Calculate target time slot
        target_time_slot = self._calculate_time_slot(task_time, duration_hours)
        
        availability = {}
        
        # Generate availability for target time slot (deterministic)
        target_items = []
        
        # Add ground truth items (these satisfy all constraints)
        for gt_item in ground_truth:
            if "seat_id" in gt_item:
                target_items.append({
                    "seat_id": gt_item["seat_id"],
                    "item_name": "Periodicals Reading Room",  # Default room name
                    "properties": ["good_wifi", "quiet"]  # Assume ground truth has good properties
                })
            elif "item_name" in gt_item:
                target_items.append({
                    "item_name": gt_item["item_name"],
                    "properties": ["good_wifi", "projector"]  # Assume good properties
                })
        
        # Add some distractor items that don't satisfy all constraints
        distractor_items = self._generate_distractor_items(building_data, constraints)
        target_items.extend(distractor_items)
        
        availability[target_time_slot] = target_items
        
        # Generate random availability for other time slots
        other_slots = ["09:00-10:30", "10:30-12:00", "14:00-15:30", "15:30-17:00"]
        for slot in other_slots:
            if slot != target_time_slot:
                availability[slot] = self._generate_random_items(building_data, 2)
        
        return availability
    
    def _generate_distractor_items(self, building_data: Dict[str, Any], constraints: List[str]) -> List[Dict[str, Any]]:
        """
        Generate distractor items that don't satisfy all constraints
        
        Args:
            building_data: Building information
            constraints: List of required constraints
            
        Returns:
            List of distractor items
        """
        distractors = []
        
        # Generate items that violate some constraints
        if "good_wifi" in constraints:
            distractors.append({
                "seat_id": "B001-STUDY_AREA-S005",
                "item_name": "Study Area",
                "properties": ["quiet"]  # Missing good_wifi
            })
        
        # Add items that are already booked (check global reservations)
        existing_bookings = [r for r in self._global_reservations if r.date == self._current_task_context.get("target_date")]
        for booking in existing_bookings[:1]:  # Add one existing booking as unavailable
            distractors.append({
                "item_name": booking.item_name,
                "properties": ["good_wifi"],
                "status": "partially_booked"  # Conflicts with target time
            })
        
        return distractors
    
    def _generate_random_availability(self, building_data: Dict[str, Any], date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate random availability for non-target locations
        
        Args:
            building_data: Building information
            date: Date for availability
            
        Returns:
            Dictionary mapping time slots to available items
        """
        availability = {}
        time_slots = ["09:00-10:30", "10:30-12:00", "14:00-15:30", "15:30-17:00", "16:30-18:00"]
        
        for slot in time_slots:
            # Randomly generate 1-3 available items per slot
            num_items = random.randint(1, 3)
            availability[slot] = self._generate_random_items(building_data, num_items)
        
        return availability
    
    def _generate_random_items(self, building_data: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        Generate random available items for a building
        
        Args:
            building_data: Building information
            count: Number of items to generate
            
        Returns:
            List of available items
        """
        items = []
        amenities = building_data.get("internal_amenities", {})
        
        item_templates = [
            "Study Room {num}",
            "Meeting Room {num}",
            "Conference Room {num}",
            "Seminar Room {num}"
        ]
        
        for i in range(count):
            template = random.choice(item_templates)
            room_num = random.randint(101, 299)
            item_name = template.format(num=room_num)
            
            items.append({
                "item_name": item_name,
                "properties": random.sample(["good_wifi", "projector", "whiteboard", "quiet"], 2)
            })
        
        return items
    
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
