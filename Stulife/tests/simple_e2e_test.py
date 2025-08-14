#!/usr/bin/env python3
"""
Simplified End-to-End Test for CampusLifeBench using Official Framework Components

This script directly uses CampusTask and related components to test our 6 task categories
with DeepSeek API integration, following the official LifelongAgentBench patterns.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
    from src.tasks.instance.campus_life_bench.environment import CampusEnvironment
    from src.factories.chat_history_item import ChatHistoryItemFactory
    from src.tasks.task import Session, SessionEvaluationOutcome
    from src.agents.instance.language_model_agent import LanguageModelAgent
    from src.language_models.instance.openai_language_model import OpenaiLanguageModel

    print("✅ LifelongAgentBench components imported successfully")

except ImportError as e:
    print(f"❌ Failed to import LifelongAgentBench components: {e}")
    traceback.print_exc()
    sys.exit(1)


class SimpleE2ETestRunner:
    """Simplified End-to-End Test Runner using Official Components"""
    
    def __init__(self):
        self.test_results = {}
        self.execution_logs = []
        self.start_time = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize LifelongAgentBench components"""
        print("🔧 Initializing components...")
        
        # Initialize language model with DeepSeek API
        self.language_model = OpenaiLanguageModel(
            model_name="deepseek-chat",
            api_key="sk-d4226415d55d492fb913479f1a8b6b9c",
            base_url="https://api.deepseek.com",
            role_dict={"user": "user", "agent": "assistant"}
        )
        print("✅ Language model initialized")
        
        # Initialize agent with empty system prompt (system prompt comes from chat history)
        # Use exact same config as test_full_flow.py
        self.agent = LanguageModelAgent(
            language_model=self.language_model,
            system_prompt="",  # Empty system prompt - will use chat history
            inference_config_dict={
                "temperature": 0.1,
                "max_tokens": 1000
            }
        )
        print("✅ Agent initialized")
        
        # Initialize task with max_round=10 as requested
        # Use a simple chat history path (we'll create a minimal one)
        chat_history_path = Path(__file__).parent / "src" / "tasks" / "instance" / "campus_life_bench" / "data" / "chat_history.json"

        # Always create/overwrite chat history with correct format
        minimal_chat_history = {
            "value": {
                "0": {"role": "user", "content": ""},
                "1": {"role": "agent", "content": ""}
            }
        }
        chat_history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chat_history_path, 'w') as f:
            json.dump(minimal_chat_history, f)

        chat_factory = ChatHistoryItemFactory(str(chat_history_path))
        self.task = CampusTask(
            chat_history_item_factory=chat_factory,
            max_round=10  # Set task retry count to 10 as requested
        )
        print("✅ CampusTask initialized with max_round=10")
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive end-to-end test"""
        print("\n🚀 Starting Official CampusLifeBench End-to-End Test")
        print("=" * 80)
        print(f"🤖 Model: deepseek-chat")
        print(f"🔄 Max Rounds per Task: 10")
        print("=" * 80)
        
        self.start_time = time.time()
        
        try:
            # Load test tasks
            tasks_data = self._load_test_tasks()
            
            # Run tests for each task
            results = self._run_all_tests(tasks_data)
            
            # Generate report
            report = self._generate_report(results)
            
            return report
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            traceback.print_exc()
            return {"error": str(e), "success": False}
    
    def _load_test_tasks(self) -> Dict[str, Any]:
        """Load test tasks from our E2E test data"""
        tasks_file = Path(__file__).parent / "src" / "tasks" / "instance" / "campus_life_bench" / "data" / "e2e_test_tasks.json"
        
        if not tasks_file.exists():
            raise FileNotFoundError(f"Test tasks file not found: {tasks_file}")
        
        with open(tasks_file, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)
        
        print(f"✅ Loaded test tasks from {tasks_file}")
        return tasks_data
    
    def _run_all_tests(self, tasks_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all test tasks"""
        results = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "test_details": {},
            "execution_times": {},
            "error_log": []
        }
        
        # Skip metadata entry
        test_tasks = {k: v for k, v in tasks_data.items() if k != "metadata"}
        
        for task_id, task_data in test_tasks.items():
            print(f"\n📋 Running Test: {task_id}")
            print("-" * 60)
            
            test_start_time = time.time()
            
            try:
                # Create dataset item
                dataset_item = CampusDatasetItem(**task_data)
                print(f"✅ Task loaded: {dataset_item.task_id}")
                print(f"📝 Instruction: {dataset_item.instruction[:100]}...")
                print(f"🔧 Available Systems: {dataset_item.available_systems}")
                
                # Run single test
                test_result = self._run_single_test(dataset_item)
                
                # Record results
                execution_time = time.time() - test_start_time
                results["execution_times"][task_id] = execution_time
                results["test_details"][task_id] = test_result
                results["total_tests"] += 1
                
                if test_result.get("success", False):
                    results["successful_tests"] += 1
                    status_icon = "✅"
                    status_text = "SUCCESS"
                else:
                    results["failed_tests"] += 1
                    status_icon = "❌"
                    status_text = "FAILED"
                
                print(f"\n{status_icon} Test Result: {status_text}")
                print(f"⏱️  Execution Time: {execution_time:.2f}s")
                print(f"🔄 Rounds Used: {test_result.get('rounds_used', 0)}/10")
                
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                results["total_tests"] += 1
                results["failed_tests"] += 1
                results["error_log"].append({
                    "task_id": task_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return results
    
    def _run_single_test(self, dataset_item: CampusDatasetItem) -> Dict[str, Any]:
        """Run a single test using official framework components"""
        try:
            # Create session using minimal required parameters (Session has defaults)
            from src.typings import SampleStatus

            # Reset task state before each test (critical for multiple tests)
            self.task.current_sample_index = None
            self.task.current_round = 0
            self.task._Task__current_dataset_item = None

            # Create session with minimal parameters (let defaults handle the rest)
            session = Session(
                sample_index=dataset_item.task_id,
                task_name="campus_life_bench",
                sample_status=SampleStatus.INITIAL
            )

            # Manually set dataset item (following test_full_flow.py pattern)
            self.task._Task__current_dataset_item = dataset_item
            self.task.current_sample_index = dataset_item.task_id

            # Call _reset directly (not reset) to avoid validation issues
            self.task._reset(session)
            
            # Run task execution loop with max_round=10
            round_count = 0
            max_rounds = self.task.max_round  # Should be 10
            
            while round_count < max_rounds:
                round_count += 1
                print(f"   🔄 Round {round_count}/{max_rounds}")
                
                # Get agent response using the correct method
                try:
                    # Check chat history before inference
                    try:
                        history_len = len(session.chat_history.__getattribute__("value"))
                        print(f"   🔍 Chat history before inference: {history_len} items")
                        if history_len > 0:
                            last_item = session.chat_history.get_item_deep_copy(-1)
                            print(f"   🔍 Last message role: {last_item.role}, content: {last_item.content[:100]}...")
                    except:
                        print("   🔍 Chat history access failed, proceeding with inference")

                    self.agent.inference(session)
                    agent_response = session.chat_history.get_item_deep_copy(-1).content
                    print(f"   📝 Agent response: {repr(agent_response)}")

                    if not agent_response.strip():
                        print("   ⚠️  Empty agent response - API call may have failed")

                except Exception as e:
                    print(f"   ❌ Agent inference failed: {e}")
                    import traceback
                    traceback.print_exc()
                    agent_response = ""

                # Process agent response using task's parser
                parsed_result = self.task._parse_agent_response(agent_response)
                print(f"   🔍 Parsed action: {parsed_result.action.value}")
                print(f"   🔍 Parsed content: {parsed_result.content}")
                
                # Execute action based on type
                if parsed_result.action.value == "execute":
                    # Use Task's _interact method to handle the agent response
                    self.task._interact(session)
                    print(f"   ⚙️  Action executed via _interact method")

                    # Continue to next round
                    continue
                        
                elif parsed_result.action.value == "finish":
                    print("   ✅ Task finished")
                    break
                    
                elif parsed_result.action.value == "invalid":
                    print("   ❌ Invalid action format")
                    break
            
            # Evaluate task using official evaluation method
            self.task._complete(session)
            
            # Determine success based on evaluation outcome
            success = session.evaluation_record.outcome == SessionEvaluationOutcome.CORRECT
            
            return {
                "success": success,
                "rounds_used": round_count,
                "evaluation_outcome": session.evaluation_record.outcome.value,
                "final_response": agent_response,
                "parsed_action": {
                    "action_type": parsed_result.action.value,
                    "content": parsed_result.content
                }
            }
            
        except Exception as e:
            print(f"   ❌ Single test execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "rounds_used": round_count if 'round_count' in locals() else 0
            }
    
    def _generate_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_time = time.time() - self.start_time
        
        report = {
            "summary": {
                "total_tests": results["total_tests"],
                "successful_tests": results["successful_tests"],
                "failed_tests": results["failed_tests"],
                "success_rate": results["successful_tests"] / results["total_tests"] if results["total_tests"] > 0 else 0,
                "total_execution_time": total_time,
                "average_execution_time": sum(results["execution_times"].values()) / len(results["execution_times"]) if results["execution_times"] else 0
            },
            "test_details": results["test_details"],
            "execution_times": results["execution_times"],
            "error_log": results["error_log"],
            "timestamp": datetime.now().isoformat(),
            "framework_info": {
                "framework": "LifelongAgentBench",
                "task_type": "CampusLifeBench",
                "api_provider": "DeepSeek",
                "model": "deepseek-chat",
                "max_rounds_per_task": 10,
                "official_components": True
            }
        }
        
        # Save report
        report_file = Path(__file__).parent / f"official_simple_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return report


def main():
    """Main entry point"""
    print("🎯 Official LifelongAgentBench CampusLifeBench End-to-End Test")
    print("=" * 80)
    
    # Create test runner
    runner = SimpleE2ETestRunner()
    
    # Run tests
    report = runner.run_comprehensive_test()
    
    # Display results
    if "error" in report:
        print(f"\n❌ Test execution failed: {report['error']}")
        return 1
    
    print(f"\n🎯 OFFICIAL END-TO-END TEST RESULTS")
    print("=" * 80)
    print(f"📊 Total Tests: {report['summary']['total_tests']}")
    print(f"✅ Successful: {report['summary']['successful_tests']}")
    print(f"❌ Failed: {report['summary']['failed_tests']}")
    print(f"📈 Success Rate: {report['summary']['success_rate']*100:.1f}%")
    print(f"⏱️  Total Time: {report['summary']['total_execution_time']:.2f}s")
    print(f"⏱️  Average Time: {report['summary']['average_execution_time']:.2f}s")
    print(f"🔄 Max Rounds per Task: 10")
    
    return 0 if report['summary']['failed_tests'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
