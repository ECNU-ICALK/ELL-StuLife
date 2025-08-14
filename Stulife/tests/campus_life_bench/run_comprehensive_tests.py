#!/usr/bin/env python3
"""
Comprehensive Test Runner for CampusLifeBench Action System

This script runs all test categories and generates detailed JSON reports
with performance metrics, system outputs, and validation results.
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
    UltraComplexIntegrationTests,
    SystemAvailabilityValidationTests,
    TemporalWeek1SimulationTests,
    ActionFormatValidationTests,
    EndToEndIntegrationTests,
    TestResultCollector
)


class ComprehensiveTestRunner:
    """Runs all test categories and generates comprehensive reports"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path(current_dir) / "test_results"
        self.output_dir.mkdir(exist_ok=True)
        self.start_time = time.time()
        self.results = {}
        
    def run_all_tests(self):
        """Run all test categories"""
        print("🚀 Starting Comprehensive CampusLifeBench Action System Tests")
        print("=" * 80)
        
        test_categories = [
            ("Single System Tests", SingleSystemTests),
            ("Multi-System Tests", MultiSystemTests),
            ("Ultra-Complex Integration", UltraComplexIntegrationTests),
            ("System Availability Validation", SystemAvailabilityValidationTests),
            ("Temporal Week 1 Simulation", TemporalWeek1SimulationTests),
            ("Action Format Validation", ActionFormatValidationTests),
            ("End-to-End Integration", EndToEndIntegrationTests)
        ]
        
        overall_results = {
            "test_suite_metadata": {
                "name": "CampusLifeBench Action System Comprehensive Test Suite",
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "total_categories": len(test_categories),
                "execution_start_time": datetime.fromtimestamp(self.start_time).isoformat()
            },
            "test_categories": {},
            "summary": {},
            "performance_metrics": {},
            "system_validation": {}
        }
        
        category_results = {}
        
        for category_name, test_class in test_categories:
            print(f"\n🧪 Running {category_name}")
            print("-" * 60)
            
            category_start = time.time()
            
            # Create test suite for this category
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Run tests with custom result collector
            runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
            result = runner.run(suite)
            
            category_time = time.time() - category_start
            
            # Collect category results
            category_results[category_name] = {
                "tests_run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "success_rate": (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0,
                "execution_time_seconds": category_time,
                "status": "PASS" if len(result.failures) == 0 and len(result.errors) == 0 else "FAIL",
                "failure_details": [{"test": str(test), "error": error} for test, error in result.failures],
                "error_details": [{"test": str(test), "error": error} for test, error in result.errors]
            }
            
            print(f"   ✅ {category_name}: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
        
        # Calculate overall metrics
        total_tests = sum(cat["tests_run"] for cat in category_results.values())
        total_failures = sum(cat["failures"] for cat in category_results.values())
        total_errors = sum(cat["errors"] for cat in category_results.values())
        total_time = time.time() - self.start_time
        
        overall_results["test_categories"] = category_results
        overall_results["summary"] = {
            "total_tests": total_tests,
            "total_failures": total_failures,
            "total_errors": total_errors,
            "overall_success_rate": (total_tests - total_failures - total_errors) / total_tests if total_tests > 0 else 0,
            "total_execution_time_seconds": total_time,
            "overall_status": "PASS" if total_failures == 0 and total_errors == 0 else "FAIL"
        }
        
        overall_results["performance_metrics"] = {
            "average_test_time_seconds": total_time / total_tests if total_tests > 0 else 0,
            "tests_per_second": total_tests / total_time if total_time > 0 else 0,
            "fastest_category": min(category_results.items(), key=lambda x: x[1]["execution_time_seconds"])[0] if category_results else None,
            "slowest_category": max(category_results.items(), key=lambda x: x[1]["execution_time_seconds"])[0] if category_results else None
        }
        
        # System validation summary
        overall_results["system_validation"] = {
            "action_parsing_validated": "Action Format Validation" in category_results and category_results["Action Format Validation"]["status"] == "PASS",
            "single_systems_validated": "Single System Tests" in category_results and category_results["Single System Tests"]["status"] == "PASS",
            "multi_system_integration_validated": "Multi-System Tests" in category_results and category_results["Multi-System Tests"]["status"] == "PASS",
            "system_availability_enforced": "System Availability Validation" in category_results and category_results["System Availability Validation"]["status"] == "PASS",
            "temporal_consistency_validated": "Temporal Week 1 Simulation" in category_results and category_results["Temporal Week 1 Simulation"]["status"] == "PASS",
            "end_to_end_integration_validated": "End-to-End Integration" in category_results and category_results["End-to-End Integration"]["status"] == "PASS",
            "ultra_complex_scenarios_validated": "Ultra-Complex Integration" in category_results and category_results["Ultra-Complex Integration"]["status"] == "PASS"
        }
        
        # Save results
        self._save_results(overall_results)
        self._print_summary(overall_results)
        
        return overall_results
    
    def _save_results(self, results: dict):
        """Save test results to JSON files"""
        # Main results file
        main_results_file = self.output_dir / f"comprehensive_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(main_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Summary file
        summary_file = self.output_dir / "latest_test_summary.json"
        summary = {
            "timestamp": results["test_suite_metadata"]["timestamp"],
            "overall_status": results["summary"]["overall_status"],
            "total_tests": results["summary"]["total_tests"],
            "success_rate": results["summary"]["overall_success_rate"],
            "execution_time": results["summary"]["total_execution_time_seconds"],
            "system_validation": results["system_validation"]
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Results saved to: {main_results_file}")
        print(f"📄 Summary saved to: {summary_file}")
    
    def _print_summary(self, results: dict):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
        summary = results["summary"]
        validation = results["system_validation"]
        
        print(f"📊 Overall Status: {'✅ PASS' if summary['overall_status'] == 'PASS' else '❌ FAIL'}")
        print(f"📈 Success Rate: {summary['overall_success_rate']:.1%}")
        print(f"🧪 Total Tests: {summary['total_tests']}")
        print(f"❌ Failures: {summary['total_failures']}")
        print(f"⚠️  Errors: {summary['total_errors']}")
        print(f"⏱️  Execution Time: {summary['total_execution_time_seconds']:.2f} seconds")
        
        print(f"\n🔧 System Validation Results:")
        for validation_name, status in validation.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {validation_name.replace('_', ' ').title()}")
        
        print(f"\n📋 Category Results:")
        for category_name, category_result in results["test_categories"].items():
            status_icon = "✅" if category_result["status"] == "PASS" else "❌"
            print(f"   {status_icon} {category_name}: {category_result['tests_run']} tests, {category_result['success_rate']:.1%} success")
        
        if summary['overall_status'] == 'PASS':
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"✅ The CampusLifeBench Action-based system is fully validated and ready for production!")
        else:
            print(f"\n⚠️  Some tests failed. Please review the detailed results.")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run comprehensive CampusLifeBench Action system tests")
    parser.add_argument("--output-dir", help="Output directory for test results", default=None)
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up output directory
    output_dir = args.output_dir or os.path.join(os.path.dirname(__file__), "test_results")
    
    # Run tests
    runner = ComprehensiveTestRunner(output_dir)
    results = runner.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results["summary"]["overall_status"] == "PASS" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
