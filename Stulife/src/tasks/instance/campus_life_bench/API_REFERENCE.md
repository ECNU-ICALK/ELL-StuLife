# CampusLifeBench API Reference

Complete API documentation for all tools and systems in CampusLifeBench.

**IMPORTANT**: All natural language communications/returns MUST use English only.

## Core Classes

### ToolResult

Standard result object for all tool operations.

```python
@dataclass
class ToolResult:
    status: ToolResultStatus  # SUCCESS, FAILURE, ERROR
    message: str             # English description for Agent
    data: Optional[Dict]     # Optional structured data
    error_code: Optional[str] # Error code for debugging
```

**Methods:**
- `is_success() -> bool`: Check if operation succeeded
- `is_failure() -> bool`: Check if operation failed
- `is_error() -> bool`: Check if operation had an error

## Email System

### send_email

Send an email to a recipient.

```python
def send_email(recipient: str, subject: str, body: str) -> ToolResult
```

**Parameters:**
- `recipient` (str): Email address of recipient (must contain @ and .)
- `subject` (str): Email subject line (required, non-empty)
- `body` (str): Email body content (required, non-empty)

**Returns:**
- Success: "Email has been successfully sent to {recipient}."
- Failure: Validation error messages

**Example:**
```python
result = env.send_email(
    "advisor@university.edu",
    "Office Hours Question", 
    "Dear Professor, when are your office hours?"
)
```

## Calendar System

### add_event

Add an event to a calendar.

```python
def add_event(calendar_id: str, event_title: str, location: str, time: str) -> ToolResult
```

**Parameters:**
- `calendar_id` (str): Calendar identifier ("self", "club_xxx")
- `event_title` (str): Title of the event
- `location` (str): Location of the event
- `time` (str): Time in format "Week X, Day, HH:MM-HH:MM"

**Permissions:**
- `self`: Full access (add, remove, update, view)
- `club_xxx`: Add and view only
- `advisor_xxx`: Query availability only

### remove_event

Remove an event from calendar (self only).

```python
def remove_event(calendar_id: str, event_id: str) -> ToolResult
```

### update_event

Update an event in calendar (self only).

```python
def update_event(calendar_id: str, event_id: str, new_details: Dict[str, Any]) -> ToolResult
```

### view_schedule

View schedule for a specific date.

```python
def view_schedule(calendar_id: str, date: str) -> ToolResult
```

### query_advisor_availability

Query advisor availability for a date.

```python
def query_advisor_availability(advisor_id: str, date: str) -> ToolResult
```

## Map and Geography System

### find_building_id

Find building ID by name or alias.

```python
def find_building_id(building_name: str) -> ToolResult
```

**Example:**
```python
result = env.find_building_id("Grand Central Library")
# Returns: building_id and building_name
```

### get_building_details

Get detailed information about a building.

```python
def get_building_details(building_id: str) -> ToolResult
```

### find_room_location

Find room location within campus.

```python
def find_room_location(room_query: str, building_id: Optional[str] = None, zone: Optional[str] = None) -> ToolResult
```

### find_optimal_path

Find optimal path between buildings.

```python
def find_optimal_path(source_building_id: str, target_building_id: str, constraints: Optional[Dict[str, Any]] = None) -> ToolResult
```

**Constraints:**
- `rain_exposure`: "Covered" or "Exposed"
- `surface`: "paved", "gravel", etc.
- `accessibility`: "wheelchair_accessible"

### query_buildings_by_property

Query buildings by properties.

```python
def query_buildings_by_property(zone: Optional[str] = None, building_type: Optional[str] = None, amenity: Optional[str] = None) -> ToolResult
```

### walk_to

Walk to a location using path information.

```python
def walk_to(path_info: Dict[str, Any]) -> ToolResult
```

**Parameters:**
- `path_info`: Dictionary with "path" key containing building ID list

### get_current_location

Get current location information.

```python
def get_current_location() -> ToolResult
```

## Reservation System

### query_availability

Query availability for a location on a date.

```python
def query_availability(location_id: str, date: str) -> ToolResult
```

**Returns:**
- Dictionary mapping time slots to available items
- Each item has properties like "good_wifi", "projector", etc.

### make_booking

Make a booking for a location/seat.

```python
def make_booking(location_id: str, item_name: str, date: str, time_slot: str, seat_id: Optional[str] = None) -> ToolResult
```

**Parameters:**
- `location_id`: Building ID
- `item_name`: Name of facility/room to book
- `date`: Date in format "Week X, Day"
- `time_slot`: Time slot in format "HH:MM-HH:MM"
- `seat_id`: Optional specific seat ID

## Information System

### list_chapters

List chapters in a book.

```python
def list_chapters(book_title: str) -> ToolResult
```

### list_sections

List sections in a chapter.

```python
def list_sections(book_title: str, chapter_title: str) -> ToolResult
```

### list_articles

List articles in a section.

```python
def list_articles(book_title: str, chapter_title: str, section_title: str) -> ToolResult
```

### view_article

View article content by title or ID.

```python
def view_article(identifier: str, by: str) -> ToolResult
```

**Parameters:**
- `identifier`: Article title or ID
- `by`: "title" or "id"

### list_by_category

List entities by category.

```python
def list_by_category(category: str, entity_type: str, level: Optional[str] = None) -> ToolResult
```

**Parameters:**
- `category`: Category to filter by
- `entity_type`: "club" or "advisor"
- `level`: For advisors - "level_1" or "level_2"

### query_by_identifier

Query entity by identifier.

```python
def query_by_identifier(identifier: str, by: str, entity_type: str) -> ToolResult
```

## Course Selection System

### browse_courses

Browse available courses with filters.

```python
def browse_courses(filters: Optional[Dict[str, Any]] = None) -> ToolResult
```

**Filters:**
- `credits`: Credit requirements (e.g., "<=3")

### add_course

Add course to draft schedule.

```python
def add_course(section_id: str) -> ToolResult
```

### remove_course

Remove course from draft schedule.

```python
def remove_course(section_id: str) -> ToolResult
```

### assign_pass

Assign pass type to a course.

```python
def assign_pass(section_id: str, pass_type: str) -> ToolResult
```

**Pass Types:**
- `S-Pass`: Always succeeds
- `A-Pass`: Succeeds if popularity < 95
- `B-Pass`: Succeeds if popularity < 85

### view_draft

View current draft schedule.

```python
def view_draft() -> ToolResult
```

### submit_draft

Submit draft for final registration.

```python
def submit_draft() -> ToolResult
```

## Error Handling

### Common Error Patterns

1. **Missing Parameters**: "Parameter X is required."
2. **Permission Denied**: "You do not have permission to..."
3. **Not Found**: "Entity X not found."
4. **Invalid Format**: "Invalid format for X."
5. **Conflict**: "Resource already booked/exists."

### Error Codes

- `MISSING_PARAM`: Required parameter missing
- `PERMISSION_DENIED`: Insufficient permissions
- `NOT_FOUND`: Entity not found
- `INVALID_FORMAT`: Invalid parameter format
- `CONFLICT`: Resource conflict
- `SYSTEM_ERROR`: Internal system error

## Data Formats

### Time Formats
- Date: "Week X, Day" (e.g., "Week 2, Saturday")
- Time: "HH:MM" (24-hour format)
- Time Range: "HH:MM-HH:MM"
- Full Time: "Week X, Day, HH:MM-HH:MM"

### Building IDs
- Format: "BXXX" (e.g., "B001", "B083")
- Dormitory: "B083" (default starting location)

### Calendar IDs
- Personal: "self"
- Club: "club_XXXX" (e.g., "club_c001")
- Advisor: "advisor_XXXX" (e.g., "advisor_T001")

### Course Codes
- Format: "DEPTXXX" (e.g., "CS101", "MATH201")

## Best Practices

### Tool Usage
1. Always check `result.is_success()` before using data
2. Read error messages for debugging information
3. Use appropriate tool for each task type
4. Validate parameters before calling tools

### Error Recovery
1. Parse error messages for specific issues
2. Retry with corrected parameters
3. Use alternative approaches when blocked
4. Check prerequisites (location, permissions)

### Performance
1. Cache building IDs and details when possible
2. Minimize redundant tool calls
3. Use batch operations when available
4. Plan paths before walking

## Examples

### Complete Email Workflow
```python
# Send email with validation
result = env.send_email(
    "advisor@university.edu",
    "Meeting Request",
    "Dear Professor, could we schedule a meeting this week?"
)

if result.is_success():
    print("Email sent successfully!")
else:
    print(f"Failed to send email: {result.message}")
```

### Complete Navigation Workflow
```python
# Find building
building_result = env.find_building_id("Grand Central Library")
if not building_result.is_success():
    print("Building not found")
    return

target_id = building_result.data["building_id"]

# Get current location
current_result = env.get_current_location()
source_id = current_result.data["building_id"]

# Find path
path_result = env.find_optimal_path(source_id, target_id)
if not path_result.is_success():
    print("No path found")
    return

# Walk to destination
walk_result = env.walk_to(path_result.data)
if walk_result.is_success():
    print("Successfully reached destination!")
```

### Complete Reservation Workflow
```python
# Query availability
availability = env.query_availability("B001", "Week 1, Saturday")
if not availability.is_success():
    print("Failed to query availability")
    return

# Make booking
booking = env.make_booking(
    "B001",
    "Study Room 201", 
    "Week 1, Saturday",
    "14:00-16:00"
)

if booking.is_success():
    print("Booking confirmed!")
```
