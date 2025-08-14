"""
Simple demonstration of precheck functionality
This script shows how the precheck feature works in practice
"""

import sys
import json
import tempfile
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def demo_precheck_functionality():
    """Demonstrate precheck functionality with simple examples"""
    print("🧪 Precheck Functionality Demo")
    print("=" * 50)
    
    try:
        # Import required modules
        from tasks.instance.campus_life_bench.task import CampusDatasetItem
        
        print("✅ Successfully imported CampusDatasetItem")
        
        # Test 1: Create task without precheck
        print("\n📋 Test 1: Task without precheck")
        normal_task = CampusDatasetItem(
            task_id="normal_email",
            task_type="email_sending",
            require_precheck=False,  # No precheck required
            instruction="Send a normal email",
            ground_truth={"recipient": "test@university.edu"}
        )
        print(f"   Task ID: {normal_task.task_id}")
        print(f"   Precheck required: {normal_task.require_precheck}")
        
        # Test 2: Create task with precheck enabled
        print("\n📋 Test 2: Task with precheck enabled")
        precheck_task = CampusDatasetItem(
            task_id="precheck_email",
            task_type="email_sending", 
            require_precheck=True,  # Precheck required
            instruction="Send an email that requires precheck",
            ground_truth={"recipient": "advisor@university.edu"}
        )
        print(f"   Task ID: {precheck_task.task_id}")
        print(f"   Precheck required: {precheck_task.require_precheck}")
        
        # Test 3: Multi-system task with precheck
        print("\n📋 Test 3: Multi-system task with precheck")
        multi_task = CampusDatasetItem(
            task_id="multi_precheck",
            task_type="multi_system",
            require_precheck=True,
            instruction="Complete multiple actions with precheck",
            ground_truth={
                "email_sent": {"recipient": "advisor@university.edu"},
                "reservation_made": {"item_name": "study_room"}
            }
        )
        print(f"   Task ID: {multi_task.task_id}")
        print(f"   Precheck required: {multi_task.require_precheck}")
        print(f"   Ground truth components: {list(multi_task.ground_truth.keys())}")
        
        # Test 4: Show task data structure
        print("\n📋 Test 4: Task data structure with precheck")
        sample_task_data = {
            "task_id": "sample_precheck_task",
            "task_type": "email_sending",
            "require_precheck": True,
            "instruction": "Send an email to your advisor",
            "ground_truth": {
                "recipient": "advisor@university.edu",
                "subject": "Office Hours",
                "body": "Dear Professor, when are your office hours?"
            }
        }
        
        print("   Sample task JSON structure:")
        print(json.dumps(sample_task_data, indent=4))
        
        # Test 5: Demonstrate precheck logic flow
        print("\n📋 Test 5: Precheck logic flow")
        print("   1. Task starts with require_precheck=True")
        print("   2. Before execution, system checks existing state")
        print("   3. If ground_truth conditions already satisfied:")
        print("      - precheck_failed = True")
        print("      - Task marked as INCORRECT")
        print("      - Details recorded in evaluation_record")
        print("   4. If no conflicts found:")
        print("      - precheck_failed = False") 
        print("      - Task proceeds normally")
        
        print("\n✅ Precheck functionality demo completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the campus_life_bench environment")
        print("💡 And run from the tests directory")
        return False
    
    except Exception as e:
        print(f"🚨 Unexpected error: {e}")
        return False


def demo_precheck_task_creation():
    """Demonstrate how to create tasks with precheck in task files"""
    print("\n📝 Creating Sample Task Files with Precheck")
    print("=" * 50)
    
    # Create sample tasks with precheck
    sample_tasks = {
        "metadata": {
            "description": "Sample tasks demonstrating precheck functionality",
            "version": "1.0"
        },
        
        "precheck_email_001": {
            "task_id": "precheck_email_001",
            "task_type": "email_sending",
            "require_precheck": True,
            "instruction": "Send an email to your advisor asking about research opportunities.",
            "ground_truth": {
                "recipient": "advisor@university.edu",
                "subject": "Research Opportunities",
                "body": "Dear Professor, I am interested in research opportunities in your lab."
            }
        },
        
        "normal_email_001": {
            "task_id": "normal_email_001", 
            "task_type": "email_sending",
            "require_precheck": False,
            "instruction": "Send an email to your advisor asking about research opportunities.",
            "ground_truth": {
                "recipient": "advisor@university.edu",
                "subject": "Research Opportunities",
                "body": "Dear Professor, I am interested in research opportunities in your lab."
            }
        },
        
        "precheck_multi_001": {
            "task_id": "precheck_multi_001",
            "task_type": "multi_system",
            "require_precheck": True,
            "require_sequence": True,
            "instruction": "Send an email to advisor and then reserve a meeting room.",
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
    
    # Create temporary file to show structure
    temp_dir = Path(tempfile.mkdtemp())
    sample_file = temp_dir / "sample_precheck_tasks.json"
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_tasks, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Sample task file created: {sample_file}")
    print("\n📋 Task file structure:")
    
    for task_id, task_data in sample_tasks.items():
        if task_id == "metadata":
            continue
        print(f"   {task_id}:")
        print(f"      - Type: {task_data['task_type']}")
        print(f"      - Precheck: {task_data.get('require_precheck', False)}")
        if 'require_sequence' in task_data:
            print(f"      - Sequence validation: {task_data['require_sequence']}")
    
    print(f"\n💡 You can copy this structure to create your own precheck tasks")
    print(f"💡 File will be cleaned up automatically")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def show_precheck_usage_examples():
    """Show practical usage examples for precheck functionality"""
    print("\n🎯 Practical Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "scenario": "Prevent duplicate emails",
            "description": "Task should fail if the same email was already sent in a previous task",
            "task_type": "email_sending",
            "use_precheck": True,
            "benefit": "Detects when agents incorrectly complete tasks early"
        },
        {
            "scenario": "Prevent duplicate reservations", 
            "description": "Task should fail if the same reservation was already made",
            "task_type": "reservation",
            "use_precheck": True,
            "benefit": "Ensures tasks are completed in correct order"
        },
        {
            "scenario": "Multi-step task validation",
            "description": "Complex task with multiple components that must be done in sequence",
            "task_type": "multi_system",
            "use_precheck": True,
            "benefit": "Validates entire workflow completion order"
        },
        {
            "scenario": "Normal task execution",
            "description": "Regular task that doesn't need precheck validation",
            "task_type": "email_sending",
            "use_precheck": False,
            "benefit": "No performance overhead for simple tasks"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n📌 Example {i}: {example['scenario']}")
        print(f"   Description: {example['description']}")
        print(f"   Task type: {example['task_type']}")
        print(f"   Use precheck: {example['use_precheck']}")
        print(f"   Benefit: {example['benefit']}")


def main():
    """Main demo function"""
    print("🚀 Starting Precheck Functionality Demo")
    print("=" * 60)
    
    # Run basic functionality demo
    success = demo_precheck_functionality()
    
    if success:
        # Show task creation examples
        demo_precheck_task_creation()
        
        # Show usage examples
        show_precheck_usage_examples()
        
        print("\n" + "=" * 60)
        print("🎉 Precheck functionality demo completed successfully!")
        print("✅ The precheck feature is ready to use")
        print("\n💡 Next steps:")
        print("   1. Add require_precheck=True to your task definitions")
        print("   2. Run tasks that might have conflicts")
        print("   3. Check evaluation_record for precheck details")
        print("   4. Use run_precheck_tests.py for comprehensive testing")
    else:
        print("\n❌ Demo encountered issues")
        print("💡 Check your environment and dependencies")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
