"""
System Prompt Generator for CampusLifeBench
Generates dynamic system prompts based on available systems
All natural language communications/returns MUST use English only
"""

from typing import List, Optional, Dict, Any
import sys
import os

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from action_executor import ActionExecutor
except ImportError:
    try:
        from .action_executor import ActionExecutor
    except ImportError:
        # Absolute import fallback
        from tasks.instance.campus_life_bench.action_executor import ActionExecutor


class SystemPromptGenerator:
    """
    Generates system prompts with tool declarations based on available systems
    """
    
    def __init__(self):
        """Initialize system prompt generator"""
        self.base_prompt = self._get_base_prompt()
        self.system_descriptions = self._get_system_descriptions()
        self.tool_descriptions = self._get_tool_descriptions()
    
    def generate_prompt(self, available_systems: Optional[List[str]] = None, task_type: Optional[str] = None) -> str:
        """
        Generate complete system prompt with available tools

        Args:
            available_systems: List of available system names (None = all systems)
            task_type: Type of task (e.g., 'quiz_question' for special handling)

        Returns:
            Complete system prompt string
        """
        if available_systems is None:
            available_systems = list(self.system_descriptions.keys())

        # Build the prompt
        prompt_parts = [self.base_prompt]

        # Add system-specific tool declarations
        for system in available_systems:
            if system in self.system_descriptions:
                prompt_parts.append(f"\n---\n### **{self.system_descriptions[system]}**\n")

                # Add tools for this system
                system_tools = self._get_tools_for_system(system)
                for tool in system_tools:
                    if tool in self.tool_descriptions:
                        prompt_parts.append(self.tool_descriptions[tool])

        return "".join(prompt_parts)

    def _get_base_prompt(self) -> str:
        """Get the base system prompt"""
        return """You are an AI agent acting as a student in a university campus environment. Your goal is to complete the tasks given to you by using a set of available tools to interact with this world.

At each step, you will be given an observation of the current state of the environment. When you receive instructions using the first person pronoun “I” , it represents what you are thinking at that moment. You need to act on it accordingly.

You have access to a variety of tools to help you. You must go to the correct location at the correct time to execute tasks. When you believe you have completed All the tasks, you MUST use the `finish()` action.

**Action Format**:
1.  **Execute only ONE action per response**.
2.  Your response MUST be wrapped in `<action>` tags.
3.  The action itself must start with `Action: `.
4.  Keep your answers as short and clear as possible.

`finish()`: Call this tool when you have completed the task. Example: `<action>Action: finish()</action>`

---
### **Responding to Questions**
When asked a multiple-choice question, you must respond in the following format:
<action>Answer: [LETTER]</action>

For example:
- <action>Answer: A</action>
- <action>Answer: B</action>
- <action>Answer: C</action>

Choose the letter that corresponds to the best answer.

---
### **Actions**

To use a tool, you must format your response as follows:

`<action>Action: tool_name(param1="value1", param2="value2")</action>`

Below is the list of tools at your disposal."""
    
    def _get_system_descriptions(self) -> Dict[str, str]:
        """Get system descriptions with emojis"""
        return {
            "email": "Email System Tools",
            "calendar": "Calendar System Tools",
            "map": "Map & Geography Tools",
            "geography": "Map & Geography Tools",
            "reservation": "Reservation System Tools",
            "bibliography": "Information & Course Tools",
            "data_system": "Information & Course Tools",
            "course_selection": "Course Selection System Tools",
            "draft": "Course Selection System Tools",
            "registration": "Course Selection System Tools",
            "student_handbook": "Student Handbook & Academic Regulations",
            "textbooks": "Textbooks & Course Materials"
        }
    
    def _get_tools_for_system(self, system: str) -> List[str]:
        """Get list of tools for a specific system"""
        system_tools = {
            "email": [
                "email.send_email",
                "email.view_inbox",
                "email.reply_email",
                "email.delete_email"
            ],
            "calendar": [
                "calendar.add_event",
                "calendar.remove_event",
                "calendar.update_event",
                "calendar.view_schedule",
                "calendar.query_advisor_availability"
            ],
            "map": [
                "map.find_building_id",
                "map.get_building_details",
                "map.find_room_location",
                "map.find_optimal_path",
                "map.query_buildings_by_property"
            ],
            "geography": [
                "geography.get_current_location",
                "geography.walk_to"
            ],
            "reservation": [
                "reservation.query_availability",
                "reservation.make_booking"
            ],
            "bibliography": [
                "bibliography.list_chapters",
                "bibliography.list_sections",
                "bibliography.list_articles",
                "bibliography.view_article"
            ],
            "data_system": [
                "data_system.list_by_category",
                "data_system.query_by_identifier",
                "data_system.list_books_by_category",
                "data_system.search_books"
            ],
            "course_selection": [
                "course_selection.browse_courses"
            ],
            "draft": [
                "draft.add_course",
                "draft.remove_course",
                "draft.assign_pass",
                "draft.view"
            ],
            "registration": [
                "registration.submit_draft"
            ],
            "student_handbook": [
                "student_handbook.available_handbooks"
            ],
            "textbooks": [
                "textbooks.available_textbooks"
            ]
        }
        return system_tools.get(system, [])
    
    def _get_tool_descriptions(self) -> Dict[str, str]:
        """Get detailed tool descriptions"""
        return {
            # Email System Tools
            "email.send_email": """* **`send_email(to: str, subject: str, body: str, cc: str = None)`**: Sends an email.
    * `to` (required): The recipient's email address.
    * `subject` (required): The subject of the email.
    * `body` (required): The content of the email.
    * *Example*: `Action: email.send_email(to="advisor.x@lau.edu", subject="Question about my schedule", body="Dear Advisor, I have a question...")`
""",
            
            "email.view_inbox": """* **`view_inbox(filter_unread: bool = None)`**: Views messages in your inbox.
    * `filter_unread` (optional): If set to `True`, shows only unread messages.
    * *Example*: `Action: email.view_inbox(filter_unread=True)`
""",
            
            "email.reply_email": """* **`reply_email(email_id: str, body: str)`**: Replies to a specific email.
    * `email_id` (required): The ID of the email you are replying to.
    * `body` (required): The content of your reply.
    * *Example*: `Action: email.reply_email(email_id="email_012", body="Thank you for the information.")`
""",
            
            "email.delete_email": """* **`delete_email(email_id: str)`**: Deletes an email from your inbox.
    * `email_id` (required): The ID of the email to delete.
    * *Example*: `Action: email.delete_email(email_id="email_013")`
""",
            
            # Calendar System Tools
            "calendar.add_event": """* **`add_event(calendar_id: str, event_title: str, location: str, time: str, description: str = None)`**: Adds an event to a calendar.
    * `calendar_id` (required): The ID of the calendar (`self`, `club_*`, `advisor_*`).
    * `event_title` (required): The title of the event.
    * `location` (required): The location of the event.
    * `time` (required): The time of the event (format: `'Week X, Day, HH:MM-HH:MM'`).
    * `description` (optional): A detailed description for the event.
    * *Example*: `Action: calendar.add_event(calendar_id="self", event_title="Team Meeting", location="Library Room 201", time="Week 3, Monday, 15:00-16:00", description="Weekly sync-up meeting.")`
""",
            
            "calendar.remove_event": """* **`remove_event(calendar_id: str, event_id: str)`**: Removes an event from a calendar.
    * `calendar_id` (required): The ID of the calendar.
    * `event_id` (required): The ID of the event to remove.
    * *Example*: `Action: calendar.remove_event(calendar_id="self", event_id="event_005")`
""",
            
            "calendar.update_event": """* **`update_event(calendar_id: str, event_id: str, new_details: dict)`**: Updates an existing event.
    * `calendar_id` (required): The ID of the calendar.
    * `event_id` (required): The ID of the event to update.
    * `new_details` (required): A dictionary with the new details (e.g., `{"location": "New Location"}`).
    * *Example*: `Action: calendar.update_event(calendar_id="self", event_id="event_006", new_details={"location": "Orwell Hall, Room 101"})`
""",
            
            "calendar.view_schedule": """* **`view_schedule(calendar_id: str, date: str)`**: Views all events on a specific date for a calendar.
    * `calendar_id` (required): The ID of the calendar to view.
    * `date` (required): The date to view (format: `'Week X, Day'`).
    * *Example*: `Action: calendar.view_schedule(calendar_id="self", date="Week 3, Monday")`
""",
            
            "calendar.query_advisor_availability": """* **`query_advisor_availability(advisor_id: str, date: str)`**: Checks an advisor's free/busy schedule.
    * `advisor_id` (required): The ID of the advisor.
    * `date` (required): The date to query (format: `'Week X, Day'`).
    * *Example*: `Action: calendar.query_advisor_availability(advisor_id="T0001", date="Week 4, Tuesday")`
""",
            
            # Map & Geography Tools
            "geography.get_current_location": """* **`get_current_location()`**: Gets your current building location.
    * *Example*: `Action: geography.get_current_location()`
""",
            
            "map.find_optimal_path": """* **`find_optimal_path(source_building_id: str, target_building_id: str, constraints: dict = None)`**: Finds the best path between two buildings.
    * `source_building_id` (required): The ID of the starting building.
    * `target_building_id` (required): The ID of the destination building.
    * `constraints` (optional): A dictionary of constraints (e.g., `{"avoid": "crowds"}`).
    * *Example*: `Action: map.find_optimal_path(source_building_id="B083", target_building_id="B001")`
""",
            
            "geography.walk_to": """* **`walk_to(path_info: dict)`**: Moves your agent along a calculated path.
    * `path_info` (required): The full path object returned by `find_optimal_path`.
    * *Example*: `Action: geography.walk_to(path_info={'path': ['B083', 'B014', 'B001']})`
""",
            
            "map.find_building_id": """* **`find_building_id(building_name: str)`**: Finds a building's unique ID by its name.
    * `building_name` (required): The name or alias of the building.
    * *Example*: `Action: map.find_building_id(building_name="Grand Central Library")`
""",
            
            "map.get_building_details": """* **`get_building_details(building_id: str)`**: Gets all details for a building.
    * `building_id` (required): The ID of the building.
    * *Example*: `Action: map.get_building_details(building_id="B001")`
""",
            
            "map.find_room_location": """* **`find_room_location(room_query: str, building_id: str = None, zone: str = None)`**: Finds the location of a specific room.
    * `room_query` (required): The name or number of the room.
    * `building_id` (optional): A specific building ID to search within.
    * *Example*: `Action: map.find_room_location(room_query="Seminar Room 101", building_id="B014")`
""",
            
            "map.query_buildings_by_property": """* **`query_buildings_by_property(...)`**: Queries buildings based on properties.
    * You can filter by `zone`, `building_type`, or `amenity`. At least one is required.
    * *Example*: `Action: map.query_buildings_by_property(amenity="Coffee Shop")`
""",
            
            # Reservation System Tools
            "reservation.query_availability": """* **`query_availability(location_id: str, date: str)`**: Queries the availability of bookable spaces in a location.
    * `location_id` (required): The ID of the building or location.
    * `date` (required): The date to query (format: `'Week X, Day'`).
    * *Example*: `Action: reservation.query_availability(location_id="B001", date="Week 4, Saturday")`
""",
            
            "reservation.make_booking": """* **`make_booking(location_id: str, item_name: str, date: str, time_slot: str, seat_id: str = None)`**: Books a specific room or seat.
    * `location_id` (required): The ID of the building.
    * `item_name` (required): The name of the room or area.
    * `date` (required): The date for the booking (format: `'Week X, Day'`).
    * `time_slot` (required): The time slot to book (e.g., `'14:00-16:00'`).
    * `seat_id` (optional): The specific seat ID if booking a seat.
    * *Example*: `Action: reservation.make_booking(location_id="B001", item_name="Group Study Room 201", date="Week 4, Saturday", time_slot="14:00-16:00")`
""",
            
            # Information & Course Tools
            "bibliography.list_chapters": """* **`list_chapters(book_title: str)`**: Lists all chapters in a book.
    * **Available Books**:
        - **Handbooks**: "Student Handbook", "Academic Integrity Guidelines", "Academic Programs Guide"
        - **Textbooks**: "A Panorama of Computing: From Bits to Artificial Intelligence", "Linear Algebra and Its Applications", "Mathematical Analysis", "Military Theory and National Defense", "Programming for Everyone", "Innovation and Entrepreneurship", "Mental Health and Wellness", "Advanced Programming Concepts"
    * *Example*: `Action: bibliography.list_chapters(book_title="Student Handbook")`
""",
            
            "bibliography.list_sections": """* **`list_sections(book_title: str, chapter_title: str)`**: Lists all sections in a chapter.
    * *Example*: `Action: bibliography.list_sections(book_title="Introduction to AI", chapter_title="Chapter 1: Search")`
""",
            
            "bibliography.list_articles": """* **`list_articles(book_title: str, chapter_title: str, section_title: str)`**: Lists all articles in a section.
    * *Example*: `Action: bibliography.list_articles(book_title="Intro to AI", chapter_title="Search", section_title="Uninformed Search")`
""",
            
            "bibliography.view_article": """* **`view_article(identifier: str, search_type: str)`**: Views the content of an article.
    * `identifier` (required): The title or ID of the article.
    * `search_type` (required): `'title'` or `'id'`.
    * *Example*: `Action: bibliography.view_article(identifier="Breadth-First Search", search_type="title")`
""",
            
            "data_system.list_by_category": """* **`list_by_category(category: str, entity_type: str, level: str = None)`**: Lists clubs or advisors by category.
    * `entity_type` (required): `'club'` or `'advisor'`.
    * **Available Club Categories**: "Academic & Technological", "Sports & Fitness", "Arts & Culture", "Community Service", "Professional Development", "Special Interest"
    * **Available Advisor Research Areas**: "Engineering", "Computer Science", "Mathematics", "Physics", "Biology", "Chemistry", "Medicine", "Social Sciences", "Humanities"
    * **Campus Information Available**: Student Clubs (101 total), Faculty Advisors (1000 total), Library Seats, Library Books (395 total)
    * *Example*: `Action: data_system.list_by_category(category="Academic & Technological", entity_type="club")`
""",
            
            "data_system.query_by_identifier": """* **`query_by_identifier(identifier: str, search_type: str, entity_type: str)`**: Gets all details for a specific club or advisor.
    * *Example*: `Action: data_system.query_by_identifier(identifier="C071", search_type="id", entity_type="club")`
""",
            
            "data_system.list_books_by_category": """* **`list_books_by_category(category: str)`**: Lists all library books in a specific category.
    * `category` (required): The category to filter by (e.g., "Computer Science", "Mathematics", "Physics", "Biology", "Literature").
    * **Library Book Categories Available**: Neuroscience, Political Science, AI, Computer Science, Mathematics, Physics, Biology, Chemistry, Literature, History, Engineering, Medicine, and many more.
    * *Example*: `Action: data_system.list_books_by_category(category="Computer Science")`
""",
            
            "data_system.search_books": """* **`search_books(query: str, search_type: str = "title")`**: Searches library books by title or author.
    * `query` (required): The search query string.
    * `search_type` (optional): `'title'` (default) or `'author'`.
    * Returns books with status information (Available/Checked Out), call numbers, and location details.
    * *Example*: `Action: data_system.search_books(query="Artificial Intelligence", search_type="title")`
    * *Example*: `Action: data_system.search_books(query="John Smith", search_type="author")`
""",
            
            # Course Selection System Tools
            "course_selection.browse_courses": """* **Course Selection Rules**:
    *   **Semester 1**: You must select at least 6 compulsory courses and a total of 8 courses.
        *   For compulsory courses, you have one S-Pass, two A-Passes, and unlimited B-Passes.
        *   For elective courses, you have one A-Pass and unlimited B-Passes.
    *   **Semester 2**: You must select at least 5 compulsory courses and a total of 7 courses.
        *   For compulsory courses, you have one S-Pass, one A-Pass, and unlimited B-Passes.
    *   **Pass Guidelines**:
        *   **S-Pass**: Guarantees enrollment in any course regardless of its popularity. It is best used for courses with a popularity of 95-99.
        *   **A-Pass**: Guarantees enrollment in courses with a popularity below 95.
        *   **B-Pass**: Can only be used for courses with a popularity below 85.

* **`browse_courses(filters: dict = None)`**: Browses available courses.
    * **Available Courses**: 226 total courses (210 from Semester 1, 16 from Semester 2)
    * **Course Types**: "Compulsory" (46 courses), "Elective" (180 courses)
    * `filters` (optional): A dictionary of filters to narrow down the search.
        - `course_code`: Partial match for the course code.
        - `course_name`: Partial, case-insensitive match for the course name.
        - `credits`: Filter by credits (e.g., `{"credits": "<=3"}`).
    * *Example*: `Action: course_selection.browse_courses(filters={"course_name": "Introduction", "credits": "<=3"})`
""",
            
            "draft.add_course": """* **`add_course(section_id: str)`**: Adds a course to your draft schedule.
    * *Example*: `Action: draft.add_course(section_id="WXK003111107")`
""",
            
            "draft.remove_course": """* **`remove_course(section_id: str)`**: Removes a course from your draft.
    * *Example*: `Action: draft.remove_course(section_id="WXK003111107")`
""",
            
            "draft.assign_pass": """* **`assign_pass(section_id: str, pass_type: str)`**: Assigns a priority pass to a drafted course.
    * `pass_type` (required): `'S-Pass'`, `'A-Pass'`, `'B-Pass'`, etc.
    * *Example*: `Action: draft.assign_pass(section_id="SHK003111017", pass_type="A-Pass")`
""",
            
            "draft.view": """* **`view_draft()`**: Views your current draft schedule.
    * *Example*: `Action: draft.view()`
""",
            
            "registration.submit_draft": """* **`submit_draft()`**: Submits your draft schedule for registration.
    * *Example*: `Action: registration.submit_draft()`
""",

            # Student Handbook & Academic Regulations
            "student_handbook.available_handbooks": """* **Available Handbooks**:
    * "Student Handbook"
    * "Academic Integrity Guidelines"
    * "Academic Programs Guide"
""",

            # Textbooks & Course Materials
            "textbooks.available_textbooks": """* **Available Textbooks**:
    * "A Panorama of Computing: From Bits to Artificial Intelligence"
    * "Linear Algebra and Its Applications"
    * "Mathematical Analysis"
    * "Military Theory and National Defense"
    * "Programming for Everyone"
    * "Innovation and Entrepreneurship"
    * "Mental Health and Wellness"
    * "Advanced Programming Concepts"
"""
        }
