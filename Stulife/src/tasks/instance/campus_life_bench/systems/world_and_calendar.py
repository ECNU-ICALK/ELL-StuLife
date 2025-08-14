"""
World Time and Calendar System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

from typing import Dict, List, Any, Optional
import uuid
from dataclasses import dataclass
import datetime

from ..tools import ToolResult, ensure_english_message


@dataclass
class CalendarEvent:
    """Represents a calendar event"""
    event_id: str
    event_title: str
    location: str
    time: str
    description: Optional[str] = None


class WorldTimeSystem:
    """
    Event-driven mock time backend
    No tools provided - all time information is injected by CampusTask
    """
    
    def __init__(self):
        """Initialize the world time system"""
        pass
    
    @staticmethod
    def generate_daily_announcement(date: str) -> str:
        """
        Generate daily announcement message
        Called by CampusTask during _reset
        
        Args:
            date: Current simulation date (e.g., "Week 2, Saturday")
            
        Returns:
            English announcement message
        """
        message = f"System Announcement: Today is {date}."
        return ensure_english_message(message)
    
    @staticmethod
    def generate_time_prompt(time: str) -> str:
        """
        Generate time prompt message
        Called by CampusTask when require_time is specified
        
        Args:
            time: Current time (e.g., "08:00")
            
        Returns:
            English time prompt message
        """
        # Convert 24-hour format to 12-hour format with AM/PM
        try:
            hour, minute = time.split(":")
            hour = int(hour)
            minute = int(minute)
            
            if hour == 0:
                time_str = f"12:{minute:02d} AM"
            elif hour < 12:
                time_str = f"{hour}:{minute:02d} AM"
            elif hour == 12:
                time_str = f"12:{minute:02d} PM"
            else:
                time_str = f"{hour-12}:{minute:02d} PM"
                
        except (ValueError, IndexError):
            # Fallback to original format if parsing fails
            time_str = time
        
        message = f"System Prompt: It is now {time_str}."
        return ensure_english_message(message)


class CalendarSystem:
    """
    Multi-identity calendar management system
    Supports personal, club, and advisor calendars with different permissions
    """
    
    def __init__(self):
        """Initialize the calendar system"""
        # Global calendars dictionary: calendar_id -> List[CalendarEvent]
        self._global_calendars: Dict[str, List[CalendarEvent]] = {
            "self": []  # Personal calendar starts empty
        }
        self._self_schedule_changes: List[Dict[str, Any]] = []

        # Permission mapping
        self._permissions = {
            "self": {"add", "remove", "update", "view"},
            # Club calendars have add and view permissions
            # Advisor calendars have query_availability permission only
        }

        # Advisor availability settings from world_state_change
        # Format: {advisor_id: {date: [available_slots]}}
        self._advisor_availability_settings: Dict[str, Dict[str, List[str]]] = {}
    
    def _ensure_calendar_exists(self, calendar_id: str) -> None:
        """Ensure calendar exists in global calendars"""
        if calendar_id not in self._global_calendars:
            self._global_calendars[calendar_id] = []
            
            # Set permissions based on calendar type
            if calendar_id.startswith("club_"):
                self._permissions[calendar_id] = {"add", "view"}
            elif calendar_id.startswith("advisor_"):
                self._permissions[calendar_id] = {"query_availability"}
            else:
                # Default permissions for other calendars
                self._permissions[calendar_id] = {"view"}
    
    def _has_permission(self, calendar_id: str, action: str) -> bool:
        """Check if action is permitted on calendar"""
        self._ensure_calendar_exists(calendar_id)
        return action in self._permissions.get(calendar_id, set())
    
    def add_event(self, calendar_id: str, event_title: str, location: str, time: str, description: Optional[str] = None) -> ToolResult:
        """
        Add an event to the specified calendar
        Permissions: self, club_id
        
        Args:
            calendar_id: Calendar identifier (e.g., "self", "club_c027")
            event_title: Title of the event
            location: Location of the event
            time: Time of the event (e.g., "Week 20, Wednesday, 15:00-17:00")
            description: Optional detailed description of the event
            
        Returns:
            ToolResult with success/failure status
        """
        try:
            # Validate inputs
            if not all([calendar_id, event_title, location, time]):
                return ToolResult.failure("All parameters (calendar_id, event_title, location, time) are required.")
            
            # Check permissions
            if not self._has_permission(calendar_id, "add"):
                return ToolResult.failure(f"You do not have permission to add events to calendar '{calendar_id}'.")
            
            # Create new event
            event_id = str(uuid.uuid4())
            event = CalendarEvent(
                event_id=event_id,
                event_title=event_title,
                location=location,
                time=time,
                description=description
            )
            
            # Add to calendar
            self._global_calendars[calendar_id].append(event)
            if calendar_id == "self":
                self._self_schedule_changes.append({
                    "action": "add",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "event": {
                        "event_id": event.event_id,
                        "event_title": event.event_title,
                        "location": event.location,
                        "time": event.time,
                        "description": event.description
                    }
                })
            
            message = f"Event '{event_title}' has been successfully added to the calendar."
            return ToolResult.success(ensure_english_message(message), {
                "event_id": event_id,
                "calendar_id": calendar_id
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to add event: {str(e)}")
    
    def remove_event(self, calendar_id: str, event_id: str) -> ToolResult:
        """
        Remove an event from the specified calendar
        Permissions: self only
        
        Args:
            calendar_id: Calendar identifier
            event_id: Event identifier to remove
            
        Returns:
            ToolResult with success/failure status
        """
        try:
            # Validate inputs
            if not all([calendar_id, event_id]):
                return ToolResult.failure("Both calendar_id and event_id are required.")
            
            # Check permissions
            if not self._has_permission(calendar_id, "remove"):
                return ToolResult.failure(f"You do not have permission to remove events from calendar '{calendar_id}'.")
            
            # Find and remove event
            calendar = self._global_calendars.get(calendar_id, [])
            for i, event in enumerate(calendar):
                if event.event_id == event_id:
                    removed_event = calendar.pop(i)
                    if calendar_id == "self":
                        self._self_schedule_changes.append({
                            "action": "remove",
                            "timestamp": datetime.datetime.now().isoformat(),
                            "event": {
                                "event_id": removed_event.event_id,
                                "event_title": removed_event.event_title,
                                "location": removed_event.location,
                                "time": removed_event.time,
                                "description": removed_event.description
                            }
                        })
                    message = f"Event '{removed_event.event_title}' has been successfully removed from the calendar."
                    return ToolResult.success(ensure_english_message(message))
            
            return ToolResult.failure(f"Event with ID '{event_id}' not found in calendar '{calendar_id}'.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to remove event: {str(e)}")
    
    def update_event(self, calendar_id: str, event_id: str, new_details: Dict[str, Any]) -> ToolResult:
        """
        Update an event in the specified calendar
        Permissions: self only
        
        Args:
            calendar_id: Calendar identifier
            event_id: Event identifier to update
            new_details: Dictionary with new event details
            
        Returns:
            ToolResult with success/failure status
        """
        try:
            # Validate inputs
            if not all([calendar_id, event_id]):
                return ToolResult.failure("Both calendar_id and event_id are required.")
            
            # Check permissions
            if not self._has_permission(calendar_id, "update"):
                return ToolResult.failure(f"You do not have permission to update events in calendar '{calendar_id}'.")
            
            # Find and update event
            calendar = self._global_calendars.get(calendar_id, [])
            for event in calendar:
                if event.event_id == event_id:
                    original_event_details = {
                        "event_id": event.event_id,
                        "event_title": event.event_title,
                        "location": event.location,
                        "time": event.time,
                        "description": event.description
                    }
                    # Update allowed fields
                    if "event_title" in new_details:
                        event.event_title = new_details["event_title"]
                    if "location" in new_details:
                        event.location = new_details["location"]
                    if "time" in new_details:
                        event.time = new_details["time"]
                    if "description" in new_details:
                        event.description = new_details["description"]

                    if calendar_id == "self":
                         self._self_schedule_changes.append({
                            "action": "update",
                            "timestamp": datetime.datetime.now().isoformat(),
                            "original_event": original_event_details,
                            "updated_event": {
                                "event_id": event.event_id,
                                "event_title": event.event_title,
                                "location": event.location,
                                "time": event.time,
                                "description": event.description
                            }
                        })
                    
                    message = f"Event '{event.event_title}' has been successfully updated."
                    return ToolResult.success(ensure_english_message(message))
            
            return ToolResult.failure(f"Event with ID '{event_id}' not found in calendar '{calendar_id}'.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to update event: {str(e)}")
    
    def view_schedule(self, calendar_id: str, date: str) -> ToolResult:
        """
        View schedule for the specified calendar and date
        Permissions: self, club_id
        
        Args:
            calendar_id: Calendar identifier
            date: Date to view (e.g., "Week 20, Wednesday")
            
        Returns:
            ToolResult with schedule information
        """
        try:
            # Validate inputs
            if not all([calendar_id, date]):
                return ToolResult.failure("Both calendar_id and date are required.")
            
            # Check permissions
            if not self._has_permission(calendar_id, "view"):
                return ToolResult.failure(f"You do not have permission to view calendar '{calendar_id}'.")
            
            # Get events for the date
            calendar = self._global_calendars.get(calendar_id, [])
            events_on_date = [event for event in calendar if date in event.time]
            
            if not events_on_date:
                message = f"No events found for {date} in calendar '{calendar_id}'."
                return ToolResult.success(ensure_english_message(message), {"events": []})
            
            # Format events for display
            event_list = []
            for event in events_on_date:
                event_details = {
                    "event_id": event.event_id,
                    "title": event.event_title,
                    "location": event.location,
                    "time": event.time,
                    "description": event.description
                }
                event_list.append(event_details)
            
            message = f"Found {len(events_on_date)} event(s) for {date}:"
            for event in events_on_date:
                message += f"\n- {event.event_title} at {event.location} ({event.time})"
                if event.description:
                    message += f"\n  Description: {event.description}"
            
            return ToolResult.success(ensure_english_message(message), {"events": event_list})
            
        except Exception as e:
            return ToolResult.error(f"Failed to view schedule: {str(e)}")
    
    def query_advisor_availability(self, advisor_id: str, date: str) -> ToolResult:
        """
        Query advisor availability for the specified date
        Returns available time slots without event details
        Permissions: any identity
        
        Args:
            advisor_id: Advisor identifier
            date: Date to query
            
        Returns:
            ToolResult with available time slots
        """
        try:
            # Validate inputs
            if not all([advisor_id, date]):
                return ToolResult.failure("Both advisor_id and date are required.")
            
            # Check if advisor availability is set via world_state_change
            if (advisor_id in self._advisor_availability_settings and
                date in self._advisor_availability_settings[advisor_id]):
                # Use world_state_change specified availability
                available_slots = self._advisor_availability_settings[advisor_id][date].copy()
            else:
                # Use default logic for dates not specified in world_state_change
                # Get advisor calendar
                calendar_id = f"advisor_{advisor_id}"
                self._ensure_calendar_exists(calendar_id)
                calendar = self._global_calendars[calendar_id]

                # Find busy time slots
                busy_slots = []
                for event in calendar:
                    if date in event.time:
                        # Extract time slot from event time
                        # Format: "Week X, Day, HH:MM-HH:MM"
                        time_parts = event.time.split(", ")
                        if len(time_parts) >= 3:
                            time_slot = time_parts[-1]  # Get the time part
                            busy_slots.append(time_slot)

                # Generate available slots (simplified - assume 9:00-17:00 working hours)
                all_slots = [
                    "09:00-10:00", "10:00-11:00", "11:00-12:00",
                    "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"
                ]

                available_slots = [slot for slot in all_slots if slot not in busy_slots]
            
            if available_slots:
                message = f"Advisor {advisor_id} is available on {date} during the following time slots: {', '.join(available_slots)}."
            else:
                message = f"Advisor {advisor_id} has no available time slots on {date}."
            
            return ToolResult.success(ensure_english_message(message), {
                "advisor_id": advisor_id,
                "date": date,
                "available_slots": available_slots
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to query advisor availability: {str(e)}")
    
    def get_and_clear_self_schedule_changes(self) -> List[Dict[str, Any]]:
        """
        Get the recorded changes for the 'self' calendar and clear the log.
        
        Returns:
            A list of dictionary objects representing the changes.
        """
        changes = self._self_schedule_changes.copy()
        self._self_schedule_changes.clear()
        return changes

    def get_calendar_events_for_evaluation(self, calendar_id: str) -> List[CalendarEvent]:
        """
        Get calendar events for evaluation purposes
        Used by CampusTask during evaluation

        Args:
            calendar_id: Calendar identifier

        Returns:
            List of CalendarEvent objects
        """
        return self._global_calendars.get(calendar_id, [])

    def set_advisor_availability(self, advisor_id: str, date: str, available_slots: List[str]) -> None:
        """
        Set advisor availability for a specific date
        Called by CampusEnvironment during world state changes

        Args:
            advisor_id: Advisor identifier (e.g., "dr.smith@lau.edu")
            date: Date string (e.g., "Week 1, Tuesday")
            available_slots: List of available time slots (e.g., ["14:00-15:00", "15:00-16:00"])
        """
        if advisor_id not in self._advisor_availability_settings:
            self._advisor_availability_settings[advisor_id] = {}

        self._advisor_availability_settings[advisor_id][date] = available_slots.copy()
