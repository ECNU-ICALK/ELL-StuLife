#!/usr/bin/env python3
"""
Detailed Test Runner for CampusLifeBench Action System

This script runs tests with comprehensive execution tracing and detailed output
showing exactly what happens during each test, including:
- Input actions
- Parsing results
- System availability checks
- Execution responses
- Validation logic
- Final judgments
"""

import unittest
import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
sys.path.insert(0, src_path)

from comprehensive_action_test_suite import (
    SingleSystemTests,
    MultiSystemTests,
    TestResultCollector
)


class DetailedTestRunner:
    """Runs tests with detailed execution tracing and output"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path(current_dir) / "detailed_test_results"
        self.output_dir.mkdir(exist_ok=True)
        self.start_time = time.time()
    
    def run_detailed_tests(self):
        """Run tests with detailed tracing"""
        print("🔍 Running Detailed CampusLifeBench Tests with Execution Tracing")
        print("=" * 80)
        
        # Test categories to run with detailed tracing
        test_categories = [
            ("Single System Tests", SingleSystemTests, ["test_email_system", "test_calendar_system", "test_quiz_question_system"]),
            ("Multi-System Tests", MultiSystemTests, ["test_email_calendar_integration"])
        ]
        
        overall_results = {
            "test_suite_metadata": {
                "name": "CampusLifeBench Detailed Test Suite",
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "execution_start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "purpose": "Detailed execution tracing and validation analysis"
            },
            "detailed_test_results": {},
            "execution_traces": {},
            "summary": {}
        }
        
        total_tests = 0
        passed_tests = 0
        
        for category_name, test_class, test_methods in test_categories:
            print(f"\n🧪 Running {category_name} with Detailed Tracing")
            print("-" * 60)
            
            category_results = {}
            category_traces = {}
            
            for test_method in test_methods:
                print(f"\n📋 Executing: {test_method}")
                
                # Create test instance
                test_instance = test_class()

                # Set up class-level attributes if needed
                if hasattr(test_class, 'setUpClass'):
                    test_class.setUpClass()

                # Set up instance
                if hasattr(test_instance, 'setUp'):
                    test_instance.setUp()
                
                try:
                    # Run the specific test method
                    method = getattr(test_instance, test_method)
                    method()
                    
                    # Collect results from the test instance
                    if hasattr(test_instance, 'result_collector'):
                        collector = test_instance.result_collector
                        
                        # Get test results
                        if category_name.replace(" ", "_").lower() in collector.results["test_categories"]:
                            test_results = collector.results["test_categories"][category_name.replace(" ", "_").lower()]
                            category_results.update(test_results)
                        
                        # Get detailed traces
                        if category_name.replace(" ", "_").lower() in collector.results["detailed_execution_traces"]:
                            test_traces = collector.results["detailed_execution_traces"][category_name.replace(" ", "_").lower()]
                            category_traces.update(test_traces)
                    
                    print(f"   ✅ {test_method} completed successfully")
                    passed_tests += 1
                    
                except Exception as e:
                    print(f"   ❌ {test_method} failed: {str(e)}")
                    category_results[test_method] = {
                        "status": "FAIL",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                
                total_tests += 1
            
            overall_results["detailed_test_results"][category_name] = category_results
            overall_results["execution_traces"][category_name] = category_traces
        
        # Calculate summary
        overall_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "execution_time_seconds": time.time() - self.start_time
        }
        
        # Save detailed results
        self._save_detailed_results(overall_results)
        self._print_detailed_summary(overall_results)
        
        return overall_results
    
    def _save_detailed_results(self, results: dict):
        """Save detailed test results with execution traces"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Main detailed results file
        detailed_file = self.output_dir / f"detailed_test_results_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Separate execution traces file for easier reading
        traces_file = self.output_dir / f"execution_traces_{timestamp}.json"
        with open(traces_file, 'w', encoding='utf-8') as f:
            json.dump(results["execution_traces"], f, indent=2, ensure_ascii=False)
        
        # Human-readable summary
        summary_file = self.output_dir / f"test_summary_{timestamp}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            self._write_human_readable_summary(f, results)
        
        print(f"\n📄 Detailed results saved to: {detailed_file}")
        print(f"📄 Execution traces saved to: {traces_file}")
        print(f"📄 Human-readable summary saved to: {summary_file}")
    
    def _write_human_readable_summary(self, file, results: dict):
        """Write human-readable summary of test results"""
        file.write("CampusLifeBench Detailed Test Results Summary\n")
        file.write("=" * 60 + "\n\n")
        
        summary = results["summary"]
        file.write(f"Overall Results:\n")
        file.write(f"  Total Tests: {summary['total_tests']}\n")
        file.write(f"  Passed: {summary['passed_tests']}\n")
        file.write(f"  Failed: {summary['failed_tests']}\n")
        file.write(f"  Success Rate: {summary['success_rate']:.1%}\n")
        file.write(f"  Execution Time: {summary['execution_time_seconds']:.2f} seconds\n\n")
        
        # Detailed execution traces
        for category, traces in results["execution_traces"].items():
            file.write(f"{category}:\n")
            file.write("-" * 40 + "\n")
            
            for test_name, trace in traces.items():
                file.write(f"\n  Test: {test_name}\n")
                file.write(f"  Description: {trace.get('test_description', 'N/A')}\n")
                file.write(f"  Task: {trace.get('task_instruction', 'N/A')}\n")
                file.write(f"  Available Systems: {trace.get('available_systems', [])}\n")
                
                if 'generated_action' in trace:
                    file.write(f"  Generated Action: {trace['generated_action']}\n")
                
                if 'action_sequence' in trace:
                    file.write(f"  Action Sequence:\n")
                    for i, action in enumerate(trace['action_sequence'], 1):
                        file.write(f"    {i}. {action}\n")
                
                # Execution trace details
                if 'execution_trace' in trace:
                    exec_trace = trace['execution_trace']
                    file.write(f"  Execution Steps:\n")
                    
                    for step in exec_trace.get('steps', []):
                        file.write(f"    - {step['step']}: {step['description']}\n")
                        file.write(f"      Success: {step.get('success', 'Unknown')}\n")
                        if 'output' in step:
                            file.write(f"      Output: {step['output']}\n")
                
                # Final judgment
                judgment = trace.get('final_judgment', {})
                file.write(f"  Final Judgment:\n")
                file.write(f"    Passed: {judgment.get('passed', 'Unknown')}\n")
                file.write(f"    Reason: {judgment.get('reason', 'N/A')}\n")
                file.write("\n")
    
    def _print_detailed_summary(self, results: dict):
        """Print detailed summary to console"""
        print("\n" + "=" * 80)
        print("🎯 DETAILED TEST RESULTS SUMMARY")
        print("=" * 80)
        
        summary = results["summary"]
        print(f"📊 Overall Status: {'✅ PASS' if summary['failed_tests'] == 0 else '❌ FAIL'}")
        print(f"📈 Success Rate: {summary['success_rate']:.1%}")
        print(f"🧪 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed_tests']}")
        print(f"❌ Failed: {summary['failed_tests']}")
        print(f"⏱️  Execution Time: {summary['execution_time_seconds']:.2f} seconds")
        
        # Show execution trace highlights
        print(f"\n🔍 Execution Trace Highlights:")
        for category, traces in results["execution_traces"].items():
            print(f"\n📋 {category}:")
            for test_name, trace in traces.items():
                judgment = trace.get('final_judgment', {})
                status_icon = "✅" if judgment.get('passed') else "❌"
                print(f"   {status_icon} {test_name}: {judgment.get('reason', 'N/A')}")
                
                # Show key execution details
                if 'execution_trace' in trace and 'steps' in trace['execution_trace']:
                    steps = trace['execution_trace']['steps']
                    for step in steps:
                        step_icon = "✅" if step.get('success') else "❌"
                        print(f"      {step_icon} {step['step']}: {step['description']}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run detailed CampusLifeBench tests with execution tracing")
    parser.add_argument("--output-dir", help="Output directory for detailed results", default=None)
    
    args = parser.parse_args()
    
    # Set up output directory
    output_dir = args.output_dir or os.path.join(os.path.dirname(__file__), "detailed_test_results")
    
    # Run detailed tests
    runner = DetailedTestRunner(output_dir)
    results = runner.run_detailed_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results["summary"]["failed_tests"] == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
