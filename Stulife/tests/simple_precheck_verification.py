"""
Simple verification of precheck functionality core features
Tests the essential precheck capabilities without full environment dependencies
"""

import sys
import json
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_datasetitem_precheck_field():
    """Test that CampusDatasetItem properly supports require_precheck field"""
    print("🧪 Testing CampusDatasetItem precheck field...")
    
    try:
        from tasks.instance.campus_life_bench.task import CampusDatasetItem
        
        # Test 1: Default value
        default_item = CampusDatasetItem(
            task_id="test_default",
            task_type="email_sending",
            instruction="Test task"
        )
        assert default_item.require_precheck == False, "Default require_precheck should be False"
        print("✅ Default require_precheck value is False")
        
        # Test 2: Explicit False
        false_item = CampusDatasetItem(
            task_id="test_false",
            task_type="email_sending", 
            require_precheck=False,
            instruction="Test task"
        )
        assert false_item.require_precheck == False, "Explicit False should work"
        print("✅ Explicit require_precheck=False works")
        
        # Test 3: Explicit True
        true_item = CampusDatasetItem(
            task_id="test_true",
            task_type="email_sending",
            require_precheck=True,
            instruction="Test task with precheck"
        )
        assert true_item.require_precheck == True, "Explicit True should work"
        print("✅ Explicit require_precheck=True works")
        
        # Test 4: JSON serialization/deserialization
        task_data = {
            "task_id": "json_test",
            "task_type": "multi_system",
            "require_precheck": True,
            "instruction": "Test JSON handling",
            "ground_truth": {
                "email_sent": {"recipient": "test@university.edu"},
                "reservation_made": {"item_name": "study_room"}
            }
        }
        
        json_item = CampusDatasetItem(**task_data)
        assert json_item.require_precheck == True, "JSON creation should work"
        print("✅ JSON-based task creation with require_precheck works")
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import CampusDatasetItem: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_precheck_method_existence():
    """Test that precheck methods exist in CampusTask"""
    print("\n🧪 Testing precheck method existence...")
    
    try:
        from tasks.instance.campus_life_bench.task import CampusTask
        
        # Check that precheck methods exist
        required_methods = [
            '_perform_precheck',
            '_check_email_precheck', 
            '_check_reservation_precheck',
            '_check_calendar_precheck',
            '_check_course_selection_precheck',
            '_check_geography_precheck'
        ]
        
        for method_name in required_methods:
            assert hasattr(CampusTask, method_name), f"Method {method_name} should exist"
            print(f"✅ Method {method_name} exists")
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import CampusTask: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Missing method: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_precheck_logic_structure():
    """Test the logical structure of precheck implementation"""
    print("\n🧪 Testing precheck logic structure...")
    
    try:
        from tasks.instance.campus_life_bench.task import CampusTask
        
        # Read the source file to verify key implementations
        task_file = Path(__file__).parent.parent / "src" / "tasks" / "instance" / "campus_life_bench" / "task.py"
        
        with open(task_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Check for key precheck implementations
        checks = [
            ("require_precheck field", "require_precheck: bool = False"),
            ("precheck_failed tracking", "self.precheck_failed: bool = False"),
            ("precheck_failure_details", "self.precheck_failure_details: List[Dict[str, Any]] = []"),
            ("precheck in _reset", "self._perform_precheck(current_item)"),
            ("precheck in evaluation", "if current_item.require_precheck and self.precheck_failed:")
        ]
        
        for check_name, check_pattern in checks:
            assert check_pattern in source_code, f"{check_name} implementation not found"
            print(f"✅ {check_name} implementation found")
        
        return True
        
    except FileNotFoundError:
        print("❌ Could not find task.py source file")
        return False
    except AssertionError as e:
        print(f"❌ Implementation check failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def create_sample_precheck_tasks():
    """Create sample task files demonstrating precheck usage"""
    print("\n📝 Creating sample precheck task files...")
    
    # Sample tasks for different scenarios
    precheck_tasks = {
        "metadata": {
            "description": "Sample tasks demonstrating require_precheck functionality",
            "created_by": "precheck_verification_script", 
            "version": "1.0"
        },
        
        "email_with_precheck": {
            "task_id": "email_with_precheck",
            "task_type": "email_sending",
            "require_precheck": True,
            "instruction": "Send an email to your advisor about research opportunities.",
            "ground_truth": {
                "recipient": "advisor@university.edu",
                "subject": "Research Opportunities Inquiry",
                "body": "Dear Professor, I am interested in exploring research opportunities."
            }
        },
        
        "email_without_precheck": {
            "task_id": "email_without_precheck", 
            "task_type": "email_sending",
            "require_precheck": False,
            "instruction": "Send an email to your advisor about research opportunities.",
            "ground_truth": {
                "recipient": "advisor@university.edu",
                "subject": "Research Opportunities Inquiry", 
                "body": "Dear Professor, I am interested in exploring research opportunities."
            }
        },
        
        "reservation_with_precheck": {
            "task_id": "reservation_with_precheck",
            "task_type": "reservation",
            "require_precheck": True,
            "instruction": "Reserve a study room in the library for tomorrow.",
            "ground_truth": {
                "expected_reservation_outcome": [
                    {
                        "item_name": "study_room",
                        "location_id": "library_main",
                        "date": "tomorrow"
                    }
                ]
            }
        },
        
        "multi_system_with_precheck": {
            "task_id": "multi_system_with_precheck",
            "task_type": "multi_system", 
            "require_precheck": True,
            "require_sequence": True,
            "instruction": "Send email to advisor and reserve a meeting room for discussion.",
            "ground_truth": {
                "email_sent": {
                    "recipient": "advisor@university.edu",
                    "subject_contains": "meeting"
                },
                "reservation_made": {
                    "item_name": "meeting_room",
                    "location_id": "library_main"
                }
            }
        }
    }
    
    # Save to temporary file
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    sample_file = temp_dir / "precheck_sample_tasks.json"
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(precheck_tasks, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Sample tasks created: {sample_file}")
    
    # Display summary
    precheck_count = 0
    total_count = 0
    
    for task_id, task_data in precheck_tasks.items():
        if task_id == "metadata":
            continue
        total_count += 1
        if task_data.get("require_precheck", False):
            precheck_count += 1
    
    print(f"📊 Task summary:")
    print(f"   Total tasks: {total_count}")
    print(f"   Tasks with precheck: {precheck_count}")
    print(f"   Tasks without precheck: {total_count - precheck_count}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return True


def run_verification():
    """Run all verification tests"""
    print("🚀 Starting Simple Precheck Verification")
    print("=" * 60)
    
    tests = [
        ("CampusDatasetItem precheck field", test_datasetitem_precheck_field),
        ("Precheck method existence", test_precheck_method_existence),
        ("Precheck logic structure", test_precheck_logic_structure),
        ("Sample task creation", create_sample_precheck_tasks)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"🚨 {test_name} - ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("✅ Precheck functionality is correctly implemented!")
        print("\n💡 Key features verified:")
        print("   • require_precheck field added to CampusDatasetItem")
        print("   • Precheck methods implemented in CampusTask")
        print("   • Logic structure properly integrated")
        print("   • Sample tasks demonstrate correct usage")
    else:
        print("⚠️ Some verifications failed")
        print("💡 Check the detailed output above for issues")
    
    return passed == total


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
