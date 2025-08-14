"""
End-to-end tests for CampusLifeBench
Tests complete workflow with mock agent
All natural language communications/returns MUST use English only
"""

import unittest
from pathlib import Path
import sys
import tempfile
import json

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
from tasks.instance.campus_life_bench.environment import CampusEnvironment
from factories.chat_history_item import ChatHistoryItemFactory
from typings import Session, SampleStatus, SessionEvaluationRecord, SessionEvaluationOutcome, Role


class MockOracleAgent:
    """Mock agent that generates correct responses for testing"""
    
    def __init__(self, task_type: str, ground_truth: dict):
        self.task_type = task_type
        self.ground_truth = ground_truth
    
    def generate_response(self) -> str:
        """Generate correct response based on task type"""
        if self.task_type == "email_sending":
            return f"""I'll send the email as requested.

```python
result = env.send_email(
    "{self.ground_truth['recipient']}",
    "{self.ground_truth['subject']}",
    "{self.ground_truth['body']}"
)
finish()
```"""
        
        elif self.task_type == "walking_simple":
            return """I need to go to the library. Let me find the path first.

```python
# Find the library building ID
building_result = env.find_building_id("Grand Central Library")
```

```python
# Find optimal path
path_result = env.find_optimal_path("B083", "B001")
```

```python
# Walk to the library
walk_result = env.walk_to(path_result.data)
```

finish()"""
        
        elif self.task_type == "calendar_management":
            gt = self.ground_truth
            return f"""I'll add the event to my calendar.

```python
result = env.add_event(
    "self",
    "{gt['event_title']}",
    "{gt['location']}",
    "{gt['time']}"
)
```

finish()"""
        
        else:
            return "finish()"


class MockSession:
    """Enhanced mock session for end-to-end testing"""
    
    def __init__(self, sample_index: str):
        self.sample_index = sample_index
        self.task_name = "campus_life_bench"
        self.sample_status = SampleStatus.INITIAL
        self.finish_reason = None
        self.task_output = None
        self.evaluation_record = SessionEvaluationRecord()
        self.chat_history = MockChatHistory()
        self.agent_responses = []


class MockChatHistory:
    """Enhanced mock chat history"""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_item_deep_copy(self, index):
        if index == -1 and self.items:
            return self.items[-1]
        return MockChatItem("test content")


class MockChatItem:
    """Mock chat item"""

    def __init__(self, content: str, role: Role = Role.AGENT):
        self.content = content
        self.role = role


class TestEndToEnd(unittest.TestCase):
    """End-to-end test cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary data directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir)
        
        # Create test data
        self._create_golden_test_data()
        
        # Create task instance with proper chat factory and data directory
        chat_history_path = Path(__file__).parent / "test_chat_history.json"
        self.chat_factory = ChatHistoryItemFactory(str(chat_history_path))

        # Create task with custom data directory
        self.task = CampusTask(self.chat_factory, max_round=10, data_dir=self.data_dir)
    
    def _create_golden_test_data(self):
        """Create golden test data with known correct answers"""
        self.tasks_data = {
            "golden_001": {
                "task_id": "golden_001",
                "task_type": "email_sending",
                "is_trigger": False,
                "instruction": "Send an email to your advisor asking about office hours.",
                "require_time": None,
                "require_place": None,
                "source_building_id": None,
                "world_state_change": [],
                "details": {
                    "recipient": "advisor@university.edu",
                    "subject": "Office Hours Inquiry",
                    "body": "Dear Professor, could you please let me know your office hours? Thank you."
                },
                "ground_truth": {
                    "recipient": "advisor@university.edu",
                    "subject": "Office Hours Inquiry",
                    "body": "Dear Professor, could you please let me know your office hours? Thank you."
                }
            },
            "golden_002": {
                "task_id": "golden_002",
                "task_type": "walking_simple",
                "is_trigger": False,
                "instruction": "Go to the Grand Central Library for your study session.",
                "require_time": None,
                "require_place": None,
                "source_building_id": "B083",
                "world_state_change": [],
                "details": {
                    "target_building": "Grand Central Library",
                    "target_building_id": "B001"
                },
                "ground_truth": {
                    "expected_outcome": {
                        "target_location_id": "B001"
                    }
                }
            },
            "golden_003": {
                "task_id": "golden_003",
                "task_type": "calendar_management",
                "is_trigger": False,
                "instruction": "Add a study group meeting to your calendar.",
                "require_time": None,
                "require_place": None,
                "source_building_id": None,
                "world_state_change": [],
                "details": {
                    "calendar_id": "self",
                    "event_title": "Study Group Meeting",
                    "location": "Library Study Room",
                    "time": "Week 1, Wednesday, 15:00-17:00"
                },
                "ground_truth": {
                    "event_title": "Study Group Meeting",
                    "location": "Library Study Room",
                    "time": "Week 1, Wednesday, 15:00-17:00"
                }
            }
        }
        
        with open(self.data_dir / "tasks.json", 'w') as f:
            json.dump(self.tasks_data, f)
        
        # Create map data with library
        map_data = {
            "nodes": [
                {
                    "id": "B083",
                    "name": "Lakeside Dormitory",
                    "aliases": ["Dorm"],
                    "type": "Residential",
                    "zone": "Residential Area",
                    "internal_amenities": {"floor_1": ["Lobby"]}
                },
                {
                    "id": "B001",
                    "name": "Grand Central Library",
                    "aliases": ["Main Library"],
                    "type": "Academic",
                    "zone": "Academic Quad",
                    "internal_amenities": {
                        "floor_1": ["Main Lobby", "Study Areas"],
                        "floor_2": ["Group Study Rooms"]
                    }
                }
            ],
            "edges": [
                {
                    "source": "B083",
                    "target": "B001",
                    "time_cost": 10,
                    "properties": {"surface": "paved", "rain_exposure": "Covered"}
                }
            ],
            "building_complexes": []
        }
        
        with open(self.data_dir / "map_v1.5.json", 'w') as f:
            json.dump(map_data, f)
        
        # Create other minimal data files
        for filename in ["bibliography.json", "campus_data.json", "courses.json"]:
            with open(self.data_dir / filename, 'w') as f:
                json.dump({}, f)
    
    def test_email_sending_workflow(self):
        """Test complete email sending workflow"""
        session = MockSession("golden_001")
        
        # Reset task first
        self.task.reset(session)
        self.assertEqual(session.sample_status, SampleStatus.RUNNING)

        # Get task data after reset
        dataset_item = self.task._get_current_dataset_item()

        # Create oracle agent
        oracle = MockOracleAgent("email_sending", dataset_item.ground_truth)
        
        # Simulate agent response
        agent_response = oracle.generate_response()
        session.chat_history.add_item(MockChatItem(agent_response))
        
        # Process agent interaction
        self.task.interact(session)

        # Complete task
        session.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session)

        # Verify correct evaluation
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.CORRECT)
        
        # Verify email was sent correctly
        latest_email = self.task.campus_environment.email_system.get_latest_email_for_evaluation()
        self.assertIsNotNone(latest_email)
        self.assertEqual(latest_email.recipient, "advisor@university.edu")
        self.assertEqual(latest_email.subject, "Office Hours Inquiry")
    
    def test_walking_workflow(self):
        """Test complete walking workflow"""
        session = MockSession("golden_002")
        
        # Reset task first
        self.task.reset(session)

        # Get task data after reset
        dataset_item = self.task._get_current_dataset_item()

        # Create oracle agent
        oracle = MockOracleAgent("walking_simple", dataset_item.ground_truth)
        
        # Test walking with correct format
        response = '''
path_result = env.find_optimal_path("B083", "B001")
if path_result.is_success():
    walk_result = env.walk_to(path_result.data)
finish()
'''
        session.chat_history.add_item(MockChatItem(f"```python{response}```"))
        self.task.interact(session)
        
        # Complete task
        session.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session)
        
        # Verify correct evaluation
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.CORRECT)

        # Verify location was updated
        geo_state = self.task.campus_environment.geography_system.get_state_for_evaluation()
        self.assertEqual(geo_state.current_location_id, "B001")
    
    def test_calendar_management_workflow(self):
        """Test complete calendar management workflow"""
        session = MockSession("golden_003")
        
        # Reset task first
        self.task.reset(session)

        # Get task data after reset
        dataset_item = self.task._get_current_dataset_item()

        # Create oracle agent
        oracle = MockOracleAgent("calendar_management", dataset_item.ground_truth)
        
        # Simulate agent response
        agent_response = oracle.generate_response()
        session.chat_history.add_item(MockChatItem(agent_response))
        
        # Process agent interaction
        self.task.interact(session)
        
        # Complete task
        session.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session)
        
        # Verify correct evaluation
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.CORRECT)
        
        # Verify event was added correctly
        events = self.task.campus_environment.calendar_system.get_calendar_events_for_evaluation("self")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_title, "Study Group Meeting")
        self.assertEqual(events[0].location, "Library Study Room")
    
    def test_state_persistence_across_tasks(self):
        """Test that state persists across multiple tasks"""
        # First task: send email
        session1 = MockSession("golden_001")
        self.task.reset(session1)
        
        # Send email
        self.task.campus_environment.send_email(
            "test1@university.edu",
            "Subject 1",
            "Body 1"
        )
        
        # Complete first task
        session1.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session1)

        # Check that email count persisted (without resetting task)
        
        # Send another email
        self.task.campus_environment.send_email(
            "test2@university.edu",
            "Subject 2", 
            "Body 2"
        )
        
        # Verify both emails are in the log
        emails = self.task.campus_environment.email_system.get_sent_emails_for_evaluation()
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].recipient, "test1@university.edu")
        self.assertEqual(emails[1].recipient, "test2@university.edu")
    
    def test_daily_reset_functionality(self):
        """Test daily reset functionality"""
        # Set initial location
        self.task.campus_environment.geography_system.set_location("B001")
        
        # Verify location is set
        geo_state = self.task.campus_environment.geography_system.get_state_for_evaluation()
        self.assertEqual(geo_state.current_location_id, "B001")
        
        # Perform daily reset
        self.task.campus_environment.daily_reset("Week 2, Monday")
        
        # Verify location is reset to dormitory
        geo_state = self.task.campus_environment.geography_system.get_state_for_evaluation()
        self.assertEqual(geo_state.current_location_id, "B083")
        self.assertEqual(len(geo_state.walk_history), 0)
    
    def test_error_handling(self):
        """Test error handling in tool execution"""
        session = MockSession("golden_001")
        self.task.reset(session)
        
        # Simulate invalid Python code
        session.chat_history.add_item(MockChatItem("""
        ```python
        invalid_syntax = 
        ```
        """))
        
        # Should handle syntax error gracefully
        try:
            self.task.interact(session)
            # Should not raise exception
        except Exception as e:
            self.fail(f"Error handling failed: {e}")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
