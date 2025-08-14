#!/usr/bin/env python3
"""
Quiz Question Demo for CampusLifeBench Action System

This script demonstrates the new quiz question functionality including:
1. Answer: format parsing
2. Quiz-specific system prompt generation
3. Multiple choice question evaluation
4. Ground truth validation for quiz answers
"""

import sys
import os
import json
from datetime import datetime

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
sys.path.insert(0, src_path)

from tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem, AgentAction
from tasks.instance.campus_life_bench.system_prompt_generator import SystemPromptGenerator


def demo_quiz_question():
    """Demonstrate quiz question functionality"""
    print("🎓 CampusLifeBench Quiz Question Demo")
    print("=" * 60)
    
    # Create quiz question scenarios
    quiz_scenarios = [
        {
            "task_id": "demo_quiz_cs",
            "task_type": "quiz_question",
            "is_trigger": False,
            "instruction": "What is the time complexity of binary search in a sorted array?\nA. O(n)\nB. O(log n)\nC. O(n log n)\nD. O(n²)\nE. O(1)",
            "available_systems": [],
            "question_type": "multiple_choice",
            "answer_format": "Answer: [LETTER]",
            "options": {
                "A": "O(n)",
                "B": "O(log n)", 
                "C": "O(n log n)",
                "D": "O(n²)",
                "E": "O(1)"
            },
            "ground_truth": "B",
            "explanation": "Binary search divides the search space in half with each comparison, resulting in O(log n) time complexity."
        },
        {
            "task_id": "demo_quiz_math",
            "task_type": "quiz_question", 
            "is_trigger": False,
            "instruction": "What is the derivative of f(x) = x³ + 2x² - 5x + 3?\nA. 3x² + 4x - 5\nB. x⁴ + 2x³ - 5x² + 3x\nC. 3x² + 2x - 5\nD. 3x² + 4x + 5\nE. x² + 4x - 5",
            "available_systems": [],
            "question_type": "multiple_choice",
            "answer_format": "Answer: [LETTER]",
            "options": {
                "A": "3x² + 4x - 5",
                "B": "x⁴ + 2x³ - 5x² + 3x", 
                "C": "3x² + 2x - 5",
                "D": "3x² + 4x + 5",
                "E": "x² + 4x - 5"
            },
            "ground_truth": "A",
            "explanation": "The derivative of x³ is 3x², the derivative of 2x² is 4x, the derivative of -5x is -5, and the derivative of a constant is 0."
        }
    ]
    
    all_results = []
    
    for i, quiz_scenario in enumerate(quiz_scenarios, 1):
        print(f"\n📋 Quiz Question {i}: {quiz_scenario['task_id']}")
        print("-" * 40)
        
        # Step 1: Display the question
        print(f"Question: {quiz_scenario['instruction']}")
        print(f"Correct Answer: {quiz_scenario['ground_truth']} - {quiz_scenario['options'][quiz_scenario['ground_truth']]}")
        
        # Step 2: Create dataset item
        dataset_item = CampusDatasetItem(**quiz_scenario)
        print(f"✅ Dataset item created for quiz question")
        
        # Step 3: Generate quiz-specific system prompt
        prompt_generator = SystemPromptGenerator()
        system_prompt = prompt_generator.generate_prompt(dataset_item.available_systems, task_type="quiz_question")
        
        print(f"✅ Quiz-specific prompt generated ({len(system_prompt)} characters)")
        print(f"   Contains Answer format instruction: {'Answer: [LETTER]' in system_prompt}")
        
        # Step 4: Test different answer formats
        test_answers = [
            f"Answer: {quiz_scenario['ground_truth']}",  # Correct answer
            "Answer: Z",  # Invalid letter
            f"Answer: {chr(ord(quiz_scenario['ground_truth']) + 1)}",  # Wrong answer
            "I think the answer is B",  # Wrong format
            f"The correct answer is {quiz_scenario['ground_truth']}"  # Wrong format
        ]
        
        answer_results = []
        
        for j, test_answer in enumerate(test_answers, 1):
            print(f"\n   Test {j}: '{test_answer}'")
            
            # Parse the answer
            parsed = CampusTask._parse_agent_response(test_answer)
            
            # Check if it's a valid quiz answer
            is_quiz_format = parsed.action == AgentAction.FINISH and parsed.finish_reason == "quiz_answer"
            
            if is_quiz_format:
                # Extract answer letter
                agent_answer = parsed.content.replace("Answer: ", "").strip().upper()
                is_correct = agent_answer == quiz_scenario["ground_truth"]
                is_valid_letter = agent_answer in ['A', 'B', 'C', 'D', 'E']
                
                print(f"      ✅ Valid quiz format: {is_quiz_format}")
                print(f"      ✅ Answer letter: {agent_answer}")
                print(f"      ✅ Valid letter: {is_valid_letter}")
                print(f"      ✅ Correct answer: {is_correct}")
                
                answer_results.append({
                    "test_answer": test_answer,
                    "parsed_correctly": True,
                    "answer_letter": agent_answer,
                    "is_correct": is_correct,
                    "is_valid_letter": is_valid_letter
                })
            else:
                print(f"      ❌ Invalid quiz format")
                print(f"      ❌ Action type: {parsed.action.value}")
                print(f"      ❌ Finish reason: {parsed.finish_reason}")
                
                answer_results.append({
                    "test_answer": test_answer,
                    "parsed_correctly": False,
                    "answer_letter": None,
                    "is_correct": False,
                    "is_valid_letter": False
                })
        
        # Step 5: Summary for this quiz
        correct_format_count = sum(1 for r in answer_results if r["parsed_correctly"])
        correct_answer_count = sum(1 for r in answer_results if r["is_correct"])
        
        print(f"\n📊 Quiz {i} Summary:")
        print(f"   ✅ Correct format parsing: {correct_format_count}/{len(test_answers)}")
        print(f"   ✅ Correct answers: {correct_answer_count}/{len(test_answers)}")
        
        all_results.append({
            "quiz_id": quiz_scenario["task_id"],
            "question": quiz_scenario["instruction"],
            "correct_answer": quiz_scenario["ground_truth"],
            "explanation": quiz_scenario["explanation"],
            "test_results": answer_results,
            "summary": {
                "correct_format_count": correct_format_count,
                "correct_answer_count": correct_answer_count,
                "total_tests": len(test_answers)
            }
        })
    
    # Overall summary
    print(f"\n🎯 OVERALL QUIZ DEMO RESULTS:")
    print("=" * 60)
    
    total_quizzes = len(all_results)
    total_tests = sum(r["summary"]["total_tests"] for r in all_results)
    total_correct_format = sum(r["summary"]["correct_format_count"] for r in all_results)
    total_correct_answers = sum(r["summary"]["correct_answer_count"] for r in all_results)
    
    print(f"📊 Quiz Questions Tested: {total_quizzes}")
    print(f"📊 Total Answer Tests: {total_tests}")
    print(f"📊 Correct Format Parsing: {total_correct_format}/{total_tests} ({total_correct_format/total_tests*100:.1f}%)")
    print(f"📊 Correct Answers: {total_correct_answers}/{total_tests} ({total_correct_answers/total_tests*100:.1f}%)")
    
    print(f"\n🔧 Quiz System Features Demonstrated:")
    print(f"   ✅ Answer: format parsing and validation")
    print(f"   ✅ Quiz-specific system prompt generation")
    print(f"   ✅ Multiple choice question handling")
    print(f"   ✅ Ground truth validation for quiz answers")
    print(f"   ✅ Invalid format rejection")
    print(f"   ✅ Letter validation (A-E only)")
    
    # Save detailed results
    report_file = f"quiz_demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "demo_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_quizzes": total_quizzes,
                "total_tests": total_tests
            },
            "quiz_results": all_results,
            "overall_summary": {
                "correct_format_rate": total_correct_format / total_tests,
                "correct_answer_rate": total_correct_answers / total_tests
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {report_file}")
    
    # Success criteria: at least 80% correct format parsing
    success = (total_correct_format / total_tests) >= 0.8
    
    if success:
        print(f"\n🎉 QUIZ DEMO COMPLETED SUCCESSFULLY!")
        print(f"✅ The quiz question system is fully functional!")
    else:
        print(f"\n⚠️  Quiz demo completed with issues.")
        print(f"❌ Format parsing rate below 80%.")
    
    return success


if __name__ == "__main__":
    success = demo_quiz_question()
    sys.exit(0 if success else 1)
