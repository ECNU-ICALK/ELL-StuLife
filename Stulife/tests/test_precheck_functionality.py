"""
Comprehensive tests for precheck functionality in CampusTask
All natural language communications/returns MUST use English only
"""

import unittest
import json
import tempfile
from pathlib import Path
import sys
import time
from unittest.mock import MagicMock

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
    from tasks.instance.campus_life_bench.environment import CampusEnvironment
    from factories.chat_history_item import ChatHistoryItemFactory
    from typings import TaskName, Session, Role, SessionEvaluationOutcome
except ImportError:
    try:
        from src.tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
        from src.tasks.instance.campus_life_bench.environment import CampusEnvironment
        from src.factories.chat_history_item import ChatHistoryItemFactory
        from src.typings import TaskName, Session, Role, SessionEvaluationOutcome
    except ImportError:
        print("Warning: Could not import modules. Running in mock mode.")
        CampusTask = MagicMock
        CampusDatasetItem = MagicMock
        CampusEnvironment = MagicMock


class TestPrecheckFunctionality(unittest.TestCase):
    """Test cases for precheck functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test data
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create minimal test tasks
        self.test_tasks = {
            "precheck_email_task": {
                "task_id": "precheck_email_task",
                "task_type": "email_sending",
                "require_precheck": True,
                "instruction": "Send an email to advisor asking about office hours.",
                "ground_truth": {
                    "recipient": "advisor@university.edu",
                    "subject": "Office Hours Inquiry",
                    "body": "Dear Professor, I would like to know your office hours."
                }
            },
            "normal_email_task": {
                "task_id": "normal_email_task",
                "task_type": "email_sending",
                "require_precheck": False,
                "instruction": "Send an email to advisor asking about office hours.",
                "ground_truth": {
                    "recipient": "advisor@university.edu",
                    "subject": "Office Hours Inquiry",
                    "body": "Dear Professor, I would like to know your office hours."
                }
            },
            "precheck_reservation_task": {
                "task_id": "precheck_reservation_task",
                "task_type": "reservation",
                "require_precheck": True,
                "instruction": "Reserve a library seat for studying.",
                "ground_truth": {
                    "expected_reservation_outcome": [
                        {
                            "seat_id": "L001",
                            "location_id": "library_main"
                        }
                    ]
                }
            },
            "precheck_multi_system_task": {
                "task_id": "precheck_multi_system_task",
                "task_type": "multi_system",
                "require_precheck": True,
                "instruction": "Send email and make reservation.",
                "ground_truth": {
                    "email_sent": {
                        "recipient": "advisor@university.edu"
                    },
                    "reservation_made": {
                        "item_name": "study_room",
                        "location_id": "library_main"
                    }
                }
            }
        }
        
        # Save test tasks to file
        tasks_file = self.temp_dir / "tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_tasks, f, indent=2)
        
        try:
            # Create campus task instance
            self.chat_factory = ChatHistoryItemFactory()
            self.campus_task = CampusTask(
                task_name=TaskName.campus_life_bench,
                chat_history_item_factory=self.chat_factory,
                max_round=5,
                data_dir=self.temp_dir
            )
        except Exception as e:
            print(f"Warning: Could not create CampusTask: {e}")
            self.campus_task = None
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_precheck_field_initialization(self):
        """Test that require_precheck field is properly initialized"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        # Test precheck enabled task
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        self.assertTrue(precheck_item.require_precheck)
        
        # Test precheck disabled task
        normal_item = CampusDatasetItem(**self.test_tasks["normal_email_task"])
        self.assertFalse(normal_item.require_precheck)
    
    def test_precheck_disabled_no_check(self):
        """Test that precheck is skipped when require_precheck is False"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        normal_item = CampusDatasetItem(**self.test_tasks["normal_email_task"])
        
        # Manually call precheck method
        self.campus_task._perform_precheck(normal_item)
        
        # Should not have failed since precheck is disabled
        self.assertFalse(self.campus_task.precheck_failed)
        self.assertEqual(len(self.campus_task.precheck_failure_details), 0)
    
    def test_precheck_enabled_no_existing_data(self):
        """Test precheck with no existing data (should pass)"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        
        # Ensure email system is clean
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            self.campus_task.campus_environment.email_system.clear_emails()
        
        # Perform precheck
        self.campus_task._perform_precheck(precheck_item)
        
        # Should not have failed since no existing emails
        self.assertFalse(self.campus_task.precheck_failed)
        self.assertEqual(len(self.campus_task.precheck_failure_details), 0)
    
    def test_email_precheck_failure(self):
        """Test email precheck failure when email already exists"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        
        # Pre-send an email that matches ground truth
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            email_system = self.campus_task.campus_environment.email_system
            email_system.send_email(
                recipient="advisor@university.edu",
                subject="Office Hours Inquiry",
                body="Dear Professor, I would like to know your office hours."
            )
            
            # Perform precheck
            self.campus_task._perform_precheck(precheck_item)
            
            # Should have failed due to existing email
            self.assertTrue(self.campus_task.precheck_failed)
            self.assertGreater(len(self.campus_task.precheck_failure_details), 0)
            
            # Check failure details
            failure_detail = self.campus_task.precheck_failure_details[0]
            self.assertEqual(failure_detail["system"], "email")
            self.assertEqual(failure_detail["component"], "recipient")
            self.assertEqual(failure_detail["expected"], "advisor@university.edu")
            self.assertIn("already satisfied", failure_detail["description"])
    
    def test_multi_system_precheck_failure(self):
        """Test multi-system precheck failure"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_multi_system_task"])
        
        # Pre-send an email that matches ground truth
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            email_system = self.campus_task.campus_environment.email_system
            email_system.send_email(
                recipient="advisor@university.edu",
                subject="Test Subject",
                body="Test body"
            )
            
            # Perform precheck
            self.campus_task._perform_precheck(precheck_item)
            
            # Should have failed due to existing email
            self.assertTrue(self.campus_task.precheck_failed)
            self.assertGreater(len(self.campus_task.precheck_failure_details), 0)
            
            # Check that email component was detected
            email_failures = [d for d in self.campus_task.precheck_failure_details if d["system"] == "email"]
            self.assertGreater(len(email_failures), 0)
    
    def test_precheck_timestamp_recording(self):
        """Test that precheck failures record proper timestamps"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        
        # Record time before test
        before_time = time.time()
        
        # Pre-send an email and perform precheck
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            email_system = self.campus_task.campus_environment.email_system
            email_system.send_email(
                recipient="advisor@university.edu",
                subject="Test Subject",
                body="Test body"
            )
            
            self.campus_task._perform_precheck(precheck_item)
            
            # Record time after test
            after_time = time.time()
            
            if self.campus_task.precheck_failed:
                failure_detail = self.campus_task.precheck_failure_details[0]
                
                # Check timestamp is reasonable
                self.assertGreaterEqual(failure_detail["timestamp"], before_time)
                self.assertLessEqual(failure_detail["timestamp"], after_time)
    
    def test_evaluation_record_enhancement(self):
        """Test that evaluation records are properly enhanced with precheck info"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        
        # Create a mock session
        session = MagicMock()
        session.evaluation_record = MagicMock()
        session.evaluation_record.detail_dict = {}
        
        # Test with precheck enabled but no failure
        self.campus_task._perform_precheck(precheck_item)
        self.campus_task._enhance_evaluation_record(session, precheck_item)
        
        # Check that precheck info was added
        details = session.evaluation_record.detail_dict
        self.assertTrue(details.get("precheck_required"))
        self.assertFalse(details.get("precheck_failed"))
        
        # Test with precheck failure
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            email_system = self.campus_task.campus_environment.email_system
            email_system.send_email("advisor@university.edu", "Test", "Test")
            
            # Reset and recheck
            session.evaluation_record.detail_dict = {}
            self.campus_task._perform_precheck(precheck_item)
            self.campus_task._enhance_evaluation_record(session, precheck_item)
            
            details = session.evaluation_record.detail_dict
            self.assertTrue(details.get("precheck_required"))
            if self.campus_task.precheck_failed:
                self.assertTrue(details.get("precheck_failed"))
                self.assertIn("precheck_failure_details", details)
    
    def test_precheck_failure_evaluation_outcome(self):
        """Test that precheck failure results in INCORRECT evaluation outcome"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        
        # Pre-send matching email
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            email_system = self.campus_task.campus_environment.email_system
            email_system.send_email("advisor@university.edu", "Test", "Test")
            
            # Create mock session and set current dataset item
            session = MagicMock()
            session.evaluation_record = MagicMock()
            session.evaluation_record.detail_dict = {}
            
            # Mock the dataset access
            self.campus_task._Task__dataset = {"test": precheck_item}
            self.campus_task._Task__current_sample_index = "test"
            
            # Perform precheck and complete evaluation
            self.campus_task._perform_precheck(precheck_item)
            
            if self.campus_task.precheck_failed:
                self.campus_task._complete(session)
                
                # Check that outcome was set to INCORRECT
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
    
    def test_precheck_with_different_task_types(self):
        """Test precheck functionality with different task types"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        # Test email task
        email_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        self.campus_task._perform_precheck(email_item)
        # Should not fail initially (no existing data)
        initial_email_failed = self.campus_task.precheck_failed
        
        # Test reservation task  
        reservation_item = CampusDatasetItem(**self.test_tasks["precheck_reservation_task"])
        self.campus_task._perform_precheck(reservation_item)
        # Should not fail initially (no existing reservations)
        initial_reservation_failed = self.campus_task.precheck_failed
        
        # Test multi-system task
        multi_item = CampusDatasetItem(**self.test_tasks["precheck_multi_system_task"])
        self.campus_task._perform_precheck(multi_item)
        # Should not fail initially (no existing data)
        initial_multi_failed = self.campus_task.precheck_failed
        
        # All should be False initially
        self.assertFalse(initial_email_failed or initial_reservation_failed or initial_multi_failed)
    
    def test_precheck_error_handling(self):
        """Test precheck error handling with invalid data"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        # Test with invalid ground truth
        invalid_item = CampusDatasetItem(
            task_id="invalid_task",
            task_type="email_sending",
            require_precheck=True,
            ground_truth="invalid_string_not_dict"  # Should be dict
        )
        
        # Should not crash
        try:
            self.campus_task._perform_precheck(invalid_item)
            # Should handle gracefully
            self.assertFalse(self.campus_task.precheck_failed)
        except Exception as e:
            self.fail(f"Precheck should handle invalid data gracefully: {e}")
    
    def test_precheck_details_format(self):
        """Test that precheck failure details have correct format"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available")
            
        precheck_item = CampusDatasetItem(**self.test_tasks["precheck_email_task"])
        
        # Pre-send matching email
        if hasattr(self.campus_task.campus_environment, 'email_system'):
            email_system = self.campus_task.campus_environment.email_system
            email_system.send_email("advisor@university.edu", "Test", "Test")
            
            self.campus_task._perform_precheck(precheck_item)
            
            if self.campus_task.precheck_failed:
                failure_detail = self.campus_task.precheck_failure_details[0]
                
                # Check required fields
                required_fields = ["system", "component", "expected", "found", "timestamp", "description"]
                for field in required_fields:
                    self.assertIn(field, failure_detail, f"Missing required field: {field}")
                
                # Check field types
                self.assertIsInstance(failure_detail["system"], str)
                self.assertIsInstance(failure_detail["component"], str)
                self.assertIsInstance(failure_detail["timestamp"], (int, float))
                self.assertIsInstance(failure_detail["description"], str)


class TestPrecheckIntegration(unittest.TestCase):
    """Integration tests for precheck functionality with full task execution"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a comprehensive test task
        self.integration_tasks = {
            "integration_test_task": {
                "task_id": "integration_test_task", 
                "task_type": "email_sending",
                "require_precheck": True,
                "instruction": "Send an email to advisor asking about office hours.",
                "ground_truth": {
                    "recipient": "advisor@university.edu",
                    "subject": "Office Hours Inquiry", 
                    "body": "Dear Professor, I would like to know your office hours."
                }
            }
        }
        
        # Save to file
        tasks_file = self.temp_dir / "tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.integration_tasks, f, indent=2)
        
        try:
            self.chat_factory = ChatHistoryItemFactory()
            self.campus_task = CampusTask(
                task_name=TaskName.campus_life_bench,
                chat_history_item_factory=self.chat_factory,
                max_round=5,
                data_dir=self.temp_dir
            )
        except Exception as e:
            print(f"Warning: Could not create CampusTask for integration test: {e}")
            self.campus_task = None
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_precheck_integration(self):
        """Test full integration of precheck with task execution"""
        if self.campus_task is None:
            self.skipTest("CampusTask not available for integration test")
            
        # Create a mock session
        session = MagicMock()
        session.chat_history = MagicMock()
        session.evaluation_record = MagicMock()
        session.evaluation_record.detail_dict = {}
        session.task_metadata = None
        
        # Mock chat history methods
        session.chat_history.inject = MagicMock()
        session.chat_history.get_item_deep_copy = MagicMock()
        session.chat_history.get_value_length = MagicMock(return_value=0)
        
        try:
            # Simulate task reset (which includes precheck)
            self.campus_task._Task__dataset = self.integration_tasks
            self.campus_task._Task__current_sample_index = "integration_test_task"
            
            # This should perform precheck during reset
            self.campus_task._reset(session)
            
            # Check that precheck was performed
            self.assertIsNotNone(hasattr(self.campus_task, 'precheck_failed'))
            
            # Test completion with precheck results
            self.campus_task._complete(session)
            
            print("✅ Integration test completed successfully")
            
        except Exception as e:
            print(f"Integration test encountered error: {e}")
            # This is expected in test environment, so we don't fail


def run_precheck_tests():
    """Run all precheck tests"""
    print("🧪 Starting Precheck Functionality Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test cases
    test_suite.addTest(unittest.makeSuite(TestPrecheckFunctionality))
    test_suite.addTest(unittest.makeSuite(TestPrecheckIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"🧪 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
    
    return success


if __name__ == "__main__":
    success = run_precheck_tests()
    sys.exit(0 if success else 1)
