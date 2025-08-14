"""
Course Selection System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from ..tools import ToolResult, ensure_english_message


@dataclass
class DraftScheduleEntry:
    """Entry in the draft schedule"""
    course_code: str
    assigned_pass: Optional[str] = None


@dataclass
class DraftSchedule:
    """Agent's draft course schedule"""
    selected_sections: List[DraftScheduleEntry]


@dataclass
class CourseState:
    """Current state of a course"""
    popularity_index: int
    seats_left: int


class CourseSelectionSystem:
    """
    Draft-based course selection system with popularity-based success rules
    Supports course browsing, draft management, and final registration
    """
    
    def __init__(self, courses_data_path: Path):
        """
        Initialize course selection system
        
        Args:
            courses_data_path: Path to courses data JSON file
        """
        self.courses_data_path = courses_data_path
        
        # Load course data
        self._courses_data: Dict[str, Any] = {}
        self._load_courses_data()
        
        # Course states (popularity and seats)
        self._course_states: Dict[str, CourseState] = {}
        self._initialize_course_states()
        
        # Agent's draft schedule
        self._draft_schedule = DraftSchedule(selected_sections=[])
    
    def _load_courses_data(self):
        """Load courses data from JSON file"""
        try:
            with open(self.courses_data_path, 'r', encoding='utf-8') as f:
                self._courses_data = json.load(f)
        except FileNotFoundError:
            # Create minimal course data if file doesn't exist
            self._courses_data = {
                "courses": [
                    {
                        "course_code": "CS101",
                        "course_name": "Introduction to Computer Science",
                        "credits": 3,
                        "total_class_hours": 48,
                        "instructor": {
                            "name": "Dr. Jane Smith",
                            "id": "T001"
                        },
                        "schedule": {
                            "weeks": {"start": 1, "end": 16},
                            "days": ["Monday", "Wednesday"],
                            "time": "10:00-11:30",
                            "class_hours_per_week": 3,
                            "location": {
                                "building_id": "B001",
                                "building_name": "Main Building",
                                "room_number": "Room 101"
                            }
                        },
                        "description": "Introduction to fundamental concepts of computer science",
                        "prerequisites": [],
                        "enrollment_capacity": 50,
                        "popularity_index": 75,
                        "seats_left": 25,
                        "type": "Compulsory"
                    }
                ]
            }
    
    def _initialize_course_states(self):
        """Initialize course states from course data"""
        for course in self._courses_data.get("courses", []):
            course_code = course["course_code"]
            self._course_states[course_code] = CourseState(
                popularity_index=course.get("popularity_index", 50),
                seats_left=course.get("seats_left", course.get("enrollment_capacity", 50))
            )
    
    def update_course_popularity(self, course_code: str, new_value: int) -> None:
        """
        Update course popularity (called by CampusEnvironment during world state changes)
        
        Args:
            course_code: Course code to update
            new_value: New popularity value
        """
        if course_code in self._course_states:
            self._course_states[course_code].popularity_index = new_value
    
    def update_course_seats(self, course_code: str, new_value: int) -> None:
        """
        Update course seats left (called by CampusEnvironment during world state changes)
        
        Args:
            course_code: Course code to update
            new_value: New seats left value
        """
        if course_code in self._course_states:
            self._course_states[course_code].seats_left = new_value
    
    def browse_courses(self, filters: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Browse available courses with optional filters
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            ToolResult with course information
        """
        try:
            courses = []
            
            for course in self._courses_data.get("courses", []):
                course_code = course["course_code"]
                
                # Apply filters if provided
                if filters:
                    # Simple filter implementation - can be extended
                    if "credits" in filters:
                        credit_filter = filters["credits"]
                        if isinstance(credit_filter, str) and "<=" in credit_filter:
                            max_credits = int(credit_filter.split("<=")[1].strip())
                            if course["credits"] > max_credits:
                                continue
                    
                    if "course_code" in filters:
                        code_filter = str(filters["course_code"])
                        if code_filter not in course.get("course_code", ""):
                            continue
                            
                    if "course_name" in filters:
                        name_filter = str(filters["course_name"])
                        if name_filter.lower() not in course.get("course_name", "").lower():
                            continue
                
                # Get current state
                state = self._course_states.get(course_code, CourseState(50, 50))
                
                # Create enriched course info
                enriched_course = course.copy()
                enriched_course["popularity_index"] = state.popularity_index
                
                courses.append(enriched_course)
            
            if not courses:
                return ToolResult.failure("No courses found matching the specified criteria.")
            
            # Format course list for display
            message = f"Found {len(courses)} course(s):"
            for course in courses:
                schedule_info = course.get("schedule", {})
                weeks = schedule_info.get("weeks", {})
                location = schedule_info.get("location", {})
                instructor = course.get("instructor", {})
                days = ", ".join(schedule_info.get("days", []))

                message += f"\n- {course['course_code']}: {course['course_name']}"
                message += f" (Credits: {course.get('credits', 'N/A')}, Popularity: {course.get('popularity_index', 'N/A')})"
                message += f"\n  Instructor: {instructor.get('name', 'N/A')}"
                message += f"\n  Schedule: Weeks {weeks.get('start', '?')}-{weeks.get('end', '?')}, {days}, {schedule_info.get('time', 'N/A')}"
                message += f"\n  Location: {location.get('building_name', 'N/A')}, {location.get('room', location.get('room_number', 'N/A'))}"

            return ToolResult.success(ensure_english_message(message), {"courses": courses})
            
        except Exception as e:
            return ToolResult.error(f"Failed to browse courses: {str(e)}")
    
    def add_course(self, section_id: str) -> ToolResult:
        """
        Add a course to draft schedule
        
        Args:
            section_id: Course section ID to add
            
        Returns:
            ToolResult indicating success or failure
        """
        try:
            if not section_id:
                return ToolResult.failure("Section ID is required.")
            
            # Check if course exists
            course_exists = any(course["course_code"] == section_id for course in self._courses_data.get("courses", []))
            if not course_exists:
                return ToolResult.failure(f"Course '{section_id}' does not exist.")
            
            # Check if already in draft
            for entry in self._draft_schedule.selected_sections:
                if entry.course_code == section_id:
                    return ToolResult.failure(f"Course '{section_id}' is already in your draft schedule.")
            
            # Add to draft
            entry = DraftScheduleEntry(course_code=section_id)
            self._draft_schedule.selected_sections.append(entry)
            
            message = f"Course '{section_id}' has been successfully added to your draft schedule."
            return ToolResult.success(ensure_english_message(message), {
                "course_code": section_id,
                "draft_count": len(self._draft_schedule.selected_sections)
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to add course: {str(e)}")
    
    def remove_course(self, section_id: str) -> ToolResult:
        """
        Remove a course from draft schedule
        
        Args:
            section_id: Course section ID to remove
            
        Returns:
            ToolResult indicating success or failure
        """
        try:
            if not section_id:
                return ToolResult.failure("Section ID is required.")
            
            # Find and remove course
            for i, entry in enumerate(self._draft_schedule.selected_sections):
                if entry.course_code == section_id:
                    removed_entry = self._draft_schedule.selected_sections.pop(i)
                    message = f"Course '{section_id}' has been successfully removed from your draft schedule."
                    return ToolResult.success(ensure_english_message(message), {
                        "course_code": section_id,
                        "draft_count": len(self._draft_schedule.selected_sections)
                    })
            
            return ToolResult.failure(f"Course '{section_id}' is not in your draft schedule.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to remove course: {str(e)}")
    
    def assign_pass(self, section_id: str, pass_type: str) -> ToolResult:
        """
        Assign a pass type to a course in draft schedule
        
        Args:
            section_id: Course section ID
            pass_type: Pass type ("S-Pass", "A-Pass", or "B-Pass")
            
        Returns:
            ToolResult indicating success or failure
        """
        try:
            if not all([section_id, pass_type]):
                return ToolResult.failure("Both section ID and pass type are required.")
            
            if pass_type not in ["S-Pass", "A-Pass", "B-Pass"]:
                return ToolResult.failure("Pass type must be 'S-Pass', 'A-Pass', or 'B-Pass'.")
            
            # Find course in draft
            for entry in self._draft_schedule.selected_sections:
                if entry.course_code == section_id:
                    entry.assigned_pass = pass_type
                    message = f"Pass type '{pass_type}' has been successfully assigned to course '{section_id}'."
                    return ToolResult.success(ensure_english_message(message), {
                        "course_code": section_id,
                        "pass_type": pass_type
                    })
            
            return ToolResult.failure(f"Course '{section_id}' is not in your draft schedule.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to assign pass: {str(e)}")
    
    def view_draft(self) -> ToolResult:
        """
        View current draft schedule
        
        Returns:
            ToolResult with draft schedule information
        """
        try:
            if not self._draft_schedule.selected_sections:
                message = "Your draft schedule is empty."
                return ToolResult.success(ensure_english_message(message), {"courses": []})
            
            message = "Your current draft schedule:"
            courses_info = []
            
            for entry in self._draft_schedule.selected_sections:
                # Get course name
                course_name = "Unknown Course"
                for course in self._courses_data.get("courses", []):
                    if course["course_code"] == entry.course_code:
                        course_name = course["course_name"]
                        break
                
                pass_info = f" (Pass: {entry.assigned_pass})" if entry.assigned_pass else " (No pass assigned)"
                message += f"\n- {entry.course_code}: {course_name}{pass_info}"
                
                courses_info.append({
                    "course_code": entry.course_code,
                    "course_name": course_name,
                    "assigned_pass": entry.assigned_pass
                })
            
            return ToolResult.success(ensure_english_message(message), {"courses": courses_info})
            
        except Exception as e:
            return ToolResult.error(f"Failed to view draft: {str(e)}")
    
    def submit_draft(self) -> ToolResult:
        """
        Submit draft schedule for final registration
        Applies deterministic rules based on popularity and pass types
        
        Returns:
            ToolResult with registration results
        """
        try:
            if not self._draft_schedule.selected_sections:
                return ToolResult.failure("Cannot submit empty draft schedule.")
            
            results = []
            success_count = 0
            
            for entry in self._draft_schedule.selected_sections:
                if not entry.assigned_pass:
                    results.append({
                        "course_code": entry.course_code,
                        "status": "Failed",
                        "reason": "No pass assigned"
                    })
                    continue
                
                # Get course popularity
                state = self._course_states.get(entry.course_code)
                if not state:
                    results.append({
                        "course_code": entry.course_code,
                        "status": "Failed",
                        "reason": "Course not found"
                    })
                    continue
                
                popularity = state.popularity_index
                
                # Apply registration rules
                success = False
                if entry.assigned_pass == "S-Pass":
                    success = True  # S-Pass always succeeds
                elif entry.assigned_pass == "A-Pass":
                    success = popularity < 95
                elif entry.assigned_pass == "B-Pass":
                    success = popularity < 85
                
                if success:
                    success_count += 1
                    results.append({
                        "course_code": entry.course_code,
                        "status": "Success",
                        "reason": f"Registered with {entry.assigned_pass}"
                    })
                else:
                    results.append({
                        "course_code": entry.course_code,
                        "status": "Failed",
                        "reason": f"Course too popular for {entry.assigned_pass} (popularity: {popularity})"
                    })
            
            # Format results message
            message = f"Registration completed! {success_count}/{len(results)} courses successfully registered:"
            for result in results:
                status_icon = "[SUCCESS]" if result["status"] == "Success" else "[FAILED]"
                message += f"\n{status_icon} {result['course_code']}: {result['status']} - {result['reason']}"
            
            return ToolResult.success(ensure_english_message(message), {
                "total_courses": len(results),
                "successful_registrations": success_count,
                "results": results
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to submit draft: {str(e)}")
    
    def get_draft_schedule_for_evaluation(self) -> DraftSchedule:
        """
        Get current draft schedule for evaluation
        Used by CampusTask during evaluation
        
        Returns:
            Current DraftSchedule object
        """
        return self._draft_schedule
    
    def get_course_states_for_evaluation(self) -> Dict[str, CourseState]:
        """
        Get current course states for evaluation
        Used by CampusTask during evaluation
        
        Returns:
            Dictionary of course states
        """
        return self._course_states.copy()
