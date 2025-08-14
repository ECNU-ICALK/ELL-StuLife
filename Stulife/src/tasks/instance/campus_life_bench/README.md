# CampusLifeBench

A comprehensive campus life simulation benchmark for evaluating AI agents in realistic university scenarios.

**IMPORTANT**: All natural language communications/returns in this benchmark MUST use English only.

## Overview

CampusLifeBench is a sophisticated evaluation framework that simulates a university campus environment where AI agents must navigate complex, multi-step tasks involving:

- **Email Communication**: Composing and sending emails to faculty and peers
- **Calendar Management**: Scheduling events and managing time
- **Campus Navigation**: Finding locations and planning optimal routes
- **Resource Reservation**: Booking study rooms and facilities
- **Information Retrieval**: Searching academic and campus databases
- **Course Selection**: Managing academic schedules and registration

## Architecture

### Core Components

1. **CampusTask**: Main task controller inheriting from LAB Task class
2. **CampusEnvironment**: Persistent world state manager
3. **ToolManager**: Tool interface and JSON generation system
4. **Subsystems**: Six specialized systems handling different aspects of campus life

### Subsystems

#### 1. World Time and Calendar System
- **WorldTimeSystem**: Event-driven time backend (no tools)
- **CalendarSystem**: Multi-identity calendar management
- **Tools**: `add_event`, `remove_event`, `update_event`, `view_schedule`, `query_advisor_availability`

#### 2. Map and Geography System
- **MapLookupSystem**: Static map information lookup
- **GeographySystem**: Agent location tracking and movement
- **Tools**: `find_building_id`, `get_building_details`, `find_room_location`, `find_optimal_path`, `query_buildings_by_property`, `walk_to`, `get_current_location`

#### 3. Reservation System
- **ReservationSystem**: Intelligent availability generation with global state persistence
- **Tools**: `query_availability`, `make_booking`

#### 4. Information System
- **InformationSystem**: Static query system for books and campus data
- **Tools**: `list_chapters`, `list_sections`, `list_articles`, `view_article`, `list_by_category`, `query_by_identifier`

#### 5. Course Selection System
- **CourseSelectionSystem**: Draft-based course selection with popularity-based success rules
- **Tools**: `browse_courses`, `add_course`, `remove_course`, `assign_pass`, `view_draft`, `submit_draft`

#### 6. Email System
- **EmailSystem**: Simple send-only email with persistent logging
- **Tools**: `send_email`

## Key Features

### Persistent World State
- Single CampusEnvironment object maintains all state across tasks
- Global reservations, email logs, and calendar events persist
- Daily reset functionality returns agent to dormitory

### Intelligent Availability Generation
- Reservation system generates deterministic availability for target locations
- Creates puzzles where only ground truth satisfies all constraints
- Random availability for non-target locations

### English-Only Enforcement
- All natural language outputs validated to be English only
- Comprehensive validation functions ensure compliance
- Error handling for non-English content

### Deterministic Path Finding
- Advanced algorithm with constraint-based penalties
- Supports rain exposure, surface type, and other path properties
- Building complex support for zero-cost internal navigation

## Usage

### Basic Setup

```python
from tasks.instance.campus_life_bench import CampusTask, CampusEnvironment
from factories.chat_history_item import ChatHistoryItemFactory

# Create task instance
chat_factory = ChatHistoryItemFactory()
task = CampusTask(chat_factory, max_round=15)

# Access environment
env = task.campus_environment
```

### Tool Usage Examples

```python
# Send an email
result = env.send_email(
    recipient="advisor@university.edu",
    subject="Office Hours Question",
    body="Dear Professor, when are your office hours this week?"
)

# Add calendar event
result = env.add_event(
    calendar_id="self",
    event_title="Study Group",
    location="Library",
    time="Week 1, Monday, 14:00-16:00"
)

# Find and walk to a building
building_result = env.find_building_id("Grand Central Library")
path_result = env.find_optimal_path("B083", "B001")
walk_result = env.walk_to(path_result.data)

# Make a reservation
availability = env.query_availability("B001", "Week 1, Saturday")
booking = env.make_booking("B001", "Study Room 201", "Week 1, Saturday", "14:00-16:00")
```

## Data Files

### Required Data Files
- `tasks.json`: Task definitions with instructions and ground truth
- `map_v1.5.json`: Campus map with buildings, paths, and properties
- `bibliography.json`: Academic book and article database
- `campus_data.json`: Club and advisor information
- `courses.json`: Course catalog with schedules and popularity

### Configuration Files
- `campus_life_bench.yaml`: Task configuration
- `test_experiment.yaml`: Experiment configuration

## Testing

### Running Tests

```bash
# Run all tests
python tests/campus_life_bench/run_tests.py

# Run specific test
python tests/campus_life_bench/run_tests.py --test test_email_system

# Run smoke test
python tests/campus_life_bench/run_tests.py --smoke

# Validate requirements
python tests/campus_life_bench/run_tests.py --validate
```

### Test Coverage
- **Unit Tests**: Individual system testing
- **Integration Tests**: CampusTask and CampusEnvironment interaction
- **End-to-End Tests**: Complete workflow with mock agents
- **Smoke Tests**: Basic functionality validation

## Evaluation

### Task Types
- `email_sending`: Email composition and delivery
- `walking_simple`: Basic campus navigation
- `calendar_management`: Event scheduling
- `reservation`: Resource booking with constraints
- `information_query`: Database searching
- `course_selection`: Academic planning

### Evaluation Criteria
- **Exact Match**: Email content, calendar events
- **Location Validation**: Precise location tracking
- **Constraint Satisfaction**: Reservation requirements
- **State Consistency**: Persistent world state

### Metrics
- Success rate by task type
- Skill-based performance analysis
- Difficulty level progression
- Error pattern analysis

## Development

### Adding New Tasks
1. Define task in `tasks.json` with ground truth
2. Implement evaluation logic in `CampusTask._complete()`
3. Add test cases for new task type
4. Update configuration files

### Extending Systems
1. Add new tools to appropriate subsystem
2. Update `CampusEnvironment` to expose tools
3. Implement evaluation logic if needed
4. Add comprehensive tests

### Quality Assurance
- All code must pass unit tests
- English-only validation required
- State consistency checks mandatory
- Performance benchmarks must be met

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed
2. **Data File Missing**: Check data directory structure
3. **Tool Execution Fails**: Validate input parameters
4. **Evaluation Incorrect**: Verify ground truth format

### Debug Mode
Enable debug logging in configuration:
```yaml
debug:
  debug_mode: true
  debug_tool_calls: true
  debug_evaluation: true
```

## License

This project is part of the LifelongAgentBench framework and follows the same licensing terms.

## Contributing

1. Follow the English-only requirement strictly
2. Add comprehensive tests for all changes
3. Update documentation for new features
4. Ensure all quality checks pass

## Contact

For questions or issues, please refer to the main LifelongAgentBench documentation or create an issue in the repository.
