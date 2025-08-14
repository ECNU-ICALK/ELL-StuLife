"""
Integration tests for CampusLifeBench
Tests interaction between CampusTask and CampusEnvironment
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
from typings import Session, SampleStatus, SessionEvaluationRecord, SessionEvaluationOutcome


class MockSession:
    """Mock session for testing"""
    
    def __init__(self, sample_index: str):
        self.sample_index = sample_index
        self.task_name = "campus_life_bench"
        self.sample_status = SampleStatus.INITIAL
        self.finish_reason = None
        self.task_output = None
        self.evaluation_record = SessionEvaluationRecord()
        self.chat_history = MockChatHistory()


class MockChatHistory:
    """Mock chat history for testing"""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_item_deep_copy(self, index):
        if index == -1 and self.items:
            return self.items[-1]
        return MockChatItem("test content")


class MockChatItem:
    """Mock chat item for testing"""
    
    def __init__(self, content: str):
        self.content = content


class TestCampusTaskIntegration(unittest.TestCase):
    """Integration tests for CampusTask"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary data directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir)
        
        # Create minimal test data
        self._create_test_data()
        
        # Create task instance with proper chat factory
        chat_history_path = Path(__file__).parent / "test_chat_history.json"
        self.chat_factory = ChatHistoryItemFactory(str(chat_history_path))
        self.task = CampusTask(self.chat_factory, max_round=5)
        
        # Override data directory
        self.task.campus_environment = CampusEnvironment(self.data_dir)
    
    def _create_test_data(self):
        """Create minimal test data files"""
        # Create tasks.json
        tasks_data = {
            "test_001": {
                "task_id": "test_001",
                "task_type": "email_sending",
                "is_trigger": False,
                "instruction": "Send a test email.",
                "require_time": None,
                "require_place": None,
                "source_building_id": None,
                "world_state_change": [],
                "details": {
                    "recipient": "test@university.edu",
                    "subject": "Test Subject",
                    "body": "Test body content"
                },
                "ground_truth": {
                    "recipient": "test@university.edu",
                    "subject": "Test Subject",
                    "body": "Test body content"
                }
            }
        }
        
        with open(self.data_dir / "tasks.json", 'w') as f:
            json.dump(tasks_data, f)
        
        # Create minimal map data
        map_data = {
            "nodes": [
                {
                    "id": "B083",
                    "name": "Lakeside Dormitory",
                    "aliases": ["Dorm"],
                    "type": "Residential",
                    "zone": "Residential Area",
                    "internal_amenities": {"floor_1": ["Lobby"]}
                }
            ],
            "edges": [],
            "building_complexes": []
        }
        
        with open(self.data_dir / "map_v1.5.json", 'w') as f:
            json.dump(map_data, f)
        
        # Create other minimal data files
        for filename in ["bibliography.json", "campus_data.json", "courses.json"]:
            with open(self.data_dir / filename, 'w') as f:
                json.dump({}, f)
    
    def test_task_initialization(self):
        """Test task initialization"""
        self.assertIsNotNone(self.task.campus_environment)
        self.assertEqual(self.task.task_name, "campus_life_bench")
        self.assertEqual(self.task.max_round, 5)
    
    def test_dataset_loading(self):
        """Test dataset loading"""
        sample_indices = self.task.get_sample_index_list()
        self.assertIn("sample_001", sample_indices)
    
    def test_reset_functionality(self):
        """Test task reset functionality"""
        session = MockSession("sample_001")
        
        # Reset should not raise exceptions
        try:
            self.task.reset(session)
            self.assertEqual(session.sample_status, SampleStatus.RUNNING)
        except Exception as e:
            self.fail(f"Reset failed with exception: {e}")
    
    def test_agent_response_parsing(self):
        """Test agent response parsing"""
        # Test finish action
        result = CampusTask._parse_agent_response("I'm done. finish()")
        self.assertEqual(result.action.value, "finish")
        
        # Test Python code execution
        result = CampusTask._parse_agent_response("""
        Here's my solution:
        ```python
        result = env.send_email("test@email.com", "Subject", "Body")
        ```
        """)
        self.assertEqual(result.action.value, "execute")
        self.assertIn("send_email", result.content)
        
        # Test invalid response
        result = CampusTask._parse_agent_response("Just some text without action")
        self.assertEqual(result.action.value, "invalid")
    
    def test_tool_execution(self):
        """Test tool execution through environment"""
        # Test email sending
        result = self.task.campus_environment.send_email(
            "test@university.edu",
            "Test Subject", 
            "Test body"
        )
        
        self.assertTrue(result.is_success())
        self.assertIn("successfully sent", result.message)
    
    def test_evaluation_email_sending(self):
        """Test evaluation for email sending task"""
        session = MockSession("sample_001")
        
        # Reset task
        self.task.reset(session)
        
        # Send correct email (matching ground truth)
        self.task.campus_environment.send_email(
            "dr.smith@university.edu",
            "Office Hours Inquiry",
            "Dear Dr. Smith, I would like to know your office hours for next week. Thank you."
        )
        
        # Complete task
        session.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session)
        
        # Check evaluation
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.CORRECT)
    
    def test_evaluation_email_sending_incorrect(self):
        """Test evaluation for incorrect email sending"""
        session = MockSession("sample_001")
        
        # Reset task
        self.task.reset(session)
        
        # Send incorrect email
        self.task.campus_environment.send_email(
            "wrong@university.edu",  # Wrong recipient
            "Test Subject",
            "Test body content"
        )
        
        # Complete task
        session.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session)
        
        # Check evaluation
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.INCORRECT)
    
    def test_evaluation_no_email_sent(self):
        """Test evaluation when no email is sent"""
        session = MockSession("sample_001")
        
        # Reset task
        self.task.reset(session)
        
        # Don't send any email
        
        # Complete task
        session.sample_status = SampleStatus.TASK_LIMIT_REACHED
        self.task.complete(session)
        
        # Check evaluation
        self.assertEqual(session.evaluation_record.outcome, SessionEvaluationOutcome.INCORRECT)
    
    def test_world_state_changes(self):
        """Test world state changes application"""
        # Create task with world state changes
        task_data = {
            "task_id": "test_002",
            "task_type": "course_selection",
            "is_trigger": False,
            "instruction": "Test instruction",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [
                {
                    "change_type": "popularity_update",
                    "course_code": "CS101",
                    "new_value": 95
                }
            ],
            "details": {},
            "ground_truth": {}
        }
        
        dataset_item = CampusDatasetItem(**task_data)
        
        # Apply world state changes
        self.task.campus_environment.apply_world_state_changes(dataset_item.world_state_change)
        
        # Check that changes were applied
        course_states = self.task.campus_environment.course_selection_system.get_course_states_for_evaluation()
        if "CS101" in course_states:
            self.assertEqual(course_states["CS101"].popularity_index, 95)
    
    def test_english_only_enforcement(self):
        """Test that all system outputs are in English"""
        # Test various tool outputs
        result = self.task.campus_environment.send_email(
            "test@university.edu",
            "Test Subject",
            "Test body"
        )
        
        # Check message is English only (ASCII characters)
        self.assertTrue(all(ord(char) < 128 for char in result.message))
        
        # Test calendar system
        result = self.task.campus_environment.add_event(
            "self",
            "Test Event",
            "Test Location",
            "Week 1, Monday, 10:00-11:00"
        )
        
        self.assertTrue(all(ord(char) < 128 for char in result.message))
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
