import os
import json
import argparse
import re
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import tiktoken
import numpy as np

def get_task_id_from_sample_index(sample_index):
    # e.g., "1060_club_task_021" -> "club_task_021"
    # e.g., "0_first_task" -> "first_task"
    # e.g., "12_course_selection_009" -> "course_selection_009"
    parts = sample_index.split('_')
    if len(parts) > 1 and parts[0].isdigit():
        return '_'.join(parts[1:])
    return sample_index

def unescape_string(s):
    if not isinstance(s, str):
        return s
    try:
        # Handle json escapes
        return json.loads(f'"{s}"')
    except (json.JSONDecodeError, TypeError):
        # Handle python-like escapes
        try:
            return s.encode('latin1').decode('unicode_escape')
        except Exception:
            return s

def compare_dicts(gt_dict, out_dict):
    """Checks if out_dict is a superset of gt_dict."""
    if not isinstance(out_dict, dict) or not isinstance(gt_dict, dict):
        return False
        
    for key, gt_value in gt_dict.items():
        out_key = key
        # Handle key variations like subject vs subject_contains
        if key.endswith('_contains'):
            out_key = key.replace('_contains', '')

        # Be more flexible about keys
        if out_key not in out_dict:
            if 'subject' in out_key and 'subject' in out_dict:
                out_key = 'subject'
            elif 'body' in out_key and 'body' in out_dict:
                out_key = 'body'
            else:
                return False

        out_value = out_dict.get(out_key)

        gt_value_unescaped = unescape_string(gt_value)
        out_value_unescaped = unescape_string(out_value)
        
        if isinstance(gt_value, str) and key.endswith('_contains'):
            if gt_value_unescaped not in str(out_value_unescaped):
                return False
        else:
            if str(gt_value_unescaped) != str(out_value_unescaped):
                return False
    return True

def compare_outputs(ground_truth, task_output):
    if not task_output or not isinstance(task_output, dict):
        return 0, len(ground_truth)

    correct_count = 0
    
    # Normalize task_output into a list of dictionaries
    output_items = []
    for value in task_output.values():
        if isinstance(value, list) and all(isinstance(i, dict) for i in value):
            output_items.extend(value)
        elif isinstance(value, dict):
            output_items.append(value)
    
    matched_output_indices = set()

    for gt_key, gt_value in ground_truth.items():
        found_match = False
        for i, out_item in enumerate(output_items):
            if i in matched_output_indices:
                continue
            
            if compare_dicts(gt_value, out_item):
                found_match = True
                matched_output_indices.add(i)
                break
        
        if found_match:
            correct_count += 1
            
    return correct_count, len(ground_truth)


def _calculate_accuracy_from_runs(list_of_runs):
    """Helper function to calculate accuracy metrics from a list of run objects."""
    total_identified = len(list_of_runs)
    
    evaluated_runs = [run for run in list_of_runs if run.get('evaluation_record', {}).get('outcome') in ['correct', 'incorrect']]
    total_evaluated = len(evaluated_runs)
    
    correct_count = sum(1 for run in evaluated_runs if run.get('evaluation_record', {}).get('outcome') == 'correct')
    
    rate = correct_count / total_evaluated if total_evaluated > 0 else 0
    return rate, correct_count, total_evaluated, total_identified


def calculate_success_rate(runs_data):
    """Calculates success rate by dividing the count of 'correct' runs by a fixed total."""
    if not runs_data:
        return "0.00%"
        
    correct_count = sum(1 for run in runs_data.values() if run.get('evaluation_record', {}).get('outcome') == 'correct')
    
    total_tasks = 939  # Fixed total number of tasks as requested.
    
    success_rate = (correct_count / total_tasks) if total_tasks > 0 else 0
    
    return f"{success_rate * 100:.2f}%"

def calculate_turn_and_token_metrics(runs_data):
    """
    Calculates turn and token metrics for ALL tasks, regardless of outcome.
    - Turns: Counts all agent messages.
    - Tokens: Counts tokens in the full chat history using tiktoken.
    """
    try:
        # Using an encoding that works for many models, like gpt-4
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback for environments where getting the encoding might fail
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

    turn_counts = []
    token_counts = []

    for run in runs_data.values():
        # Calculate turns for this task
        agent_turns = sum(1 for message in run.get('chat_history', {}).get('value', []) if message.get('role') == 'agent')
        turn_counts.append(agent_turns)

        # Calculate tokens for this task
        full_history = "".join([
            message.get('content', '') for message in run.get('chat_history', {}).get('value', [])
        ])
        token_count = len(encoding.encode(full_history))
        token_counts.append(token_count)

    if not turn_counts: # This also implies token_counts is empty
        return {
            "avg_turns": 0, "max_turns": 0, "min_turns": 0, "median_turns": 0,
            "avg_tokens": 0, "max_tokens": 0, "min_tokens": 0, "median_tokens": 0,
            "total_task_count": 0
        }

    return {
        "avg_turns": sum(turn_counts) / len(turn_counts),
        "max_turns": max(turn_counts),
        "min_turns": min(turn_counts),
        "median_turns": np.median(turn_counts),
        "avg_tokens": sum(token_counts) / len(token_counts),
        "max_tokens": max(token_counts),
        "min_tokens": min(token_counts),
        "median_tokens": np.median(token_counts),
        "total_task_count": len(turn_counts)
    }

def calculate_category_metrics(runs_list):
    """Calculates success rate and average turns for a given list of runs."""
    if not runs_list:
        return {
            "success_rate": 0,
            "avg_turns": 0,
            "task_count": 0
        }

    # Success Rate
    evaluatable_runs = [run for run in runs_list if run.get('evaluation_record', {}).get('outcome') in ['correct', 'incorrect']]
    correct_runs = [run for run in evaluatable_runs if run.get('evaluation_record', {}).get('outcome') == 'correct']
    success_rate = len(correct_runs) / len(evaluatable_runs) if evaluatable_runs else 0

    # Avg Turns (calculated over all tasks in the category)
    total_turns = 0
    for run in runs_list:
        agent_turns = sum(1 for message in run.get('chat_history', {}).get('value', []) if message.get('role') == 'agent')
        total_turns += agent_turns
    
    avg_turns = total_turns / len(runs_list) if runs_list else 0
    
    return {
        "success_rate": success_rate,
        "avg_turns": avg_turns,
        "task_count": len(runs_list)
    }

def calculate_exam_performance(runs_data):
    exam_runs = [run for si, run in runs_data.items() if 'exam_' in si]
    rate, correct, evaluated, identified = _calculate_accuracy_from_runs(exam_runs)
    score = rate * 50
    return score, correct, evaluated, identified

def calculate_class_performance(runs_data, tasks_data, task_id_to_run_map):
    class_task_ids = {
        task.get('task_id') for task in tasks_data.values()
        if task and task.get('task_type') == 'quiz_question'
        and not task.get('is_trigger', False)
        and 'exam_' not in task.get('task_id', '')
    }
    
    task_defs_by_id = {task.get('task_id'): task for task in tasks_data.values() if task and 'task_id' in task}

    total_points = 0.0
    evaluated_count = 0
    fully_correct = 0
    correct_location_wrong_answer = 0
    
    class_runs = [task_id_to_run_map[task_id] for task_id in class_task_ids if task_id in task_id_to_run_map]
    identified_count = len(class_runs)

    for run in class_runs:
        eval_record = run.get('evaluation_record', {})
        outcome = eval_record.get('outcome')

        if outcome not in ['correct', 'incorrect']:
            continue

        evaluated_count += 1
        
        if outcome == 'correct':
            total_points += 1.0
            fully_correct += 1
        else:  # outcome == 'incorrect'
            task_id = get_task_id_from_sample_index(run.get('sample_index', ''))
            task_def = task_defs_by_id.get(task_id)
            location_match = False
            if task_def:
                require_place = task_def.get('require_place')
                if require_place:
                    detail_dict = eval_record.get('detail_dict', {})
                    if detail_dict:
                        final_location = detail_dict.get('final_location')
                        if final_location and require_place == final_location:
                            total_points += 0.5
                            correct_location_wrong_answer += 1
                            location_match = True

    did_not_arrive = evaluated_count - fully_correct - correct_location_wrong_answer

    rate = total_points / evaluated_count if evaluated_count > 0 else 0
    score = rate * 30
    
    breakdown = {
        "fully_correct": fully_correct,
        "correct_location_wrong_answer": correct_location_wrong_answer,
        "did_not_arrive": did_not_arrive
    }
    
    return score, total_points, evaluated_count, identified_count, breakdown

def calculate_advisor_tasks(runs_data):
    advisor_runs = [run for si, run in runs_data.items() if 'advisor_assigned' in si]
    rate, correct, evaluated, identified = _calculate_accuracy_from_runs(advisor_runs)
    score = rate * 8
    return score, correct, evaluated, identified

def calculate_club_activities(runs_data):
    club_runs = [run for si, run in runs_data.items() if 'club_task_' in si]
    rate, correct, evaluated, identified = _calculate_accuracy_from_runs(club_runs)
    score = rate * 6
    return score, correct, evaluated, identified

def calculate_personal_responsibility(runs_data, tasks_data, task_id_to_run_map):
    # This metric is described as a score that starts at 6 and is reduced for infractions.
    # The calculation details seem to be missing from require.md.
    # I will calculate the success rate as a proxy, as hinted by other sections.
    # The logic is: find tasks that require physical presence and are not quizzes.
    
    responsible_task_ids = {
        task.get('task_id') for task in tasks_data.values()
        if task and task.get('require_place') is not None
        and task.get('task_type') != 'quiz_question'
    }

    responsible_runs = [task_id_to_run_map[task_id] for task_id in responsible_task_ids if task_id in task_id_to_run_map]
    rate, correct, evaluated, identified = _calculate_accuracy_from_runs(responsible_runs)
    score = rate * 6
    return score, correct, evaluated, identified

def calculate_stu_gpa(runs_data, tasks_data, task_id_to_run_map):
    exam_score, exam_correct, exam_eval, exam_ident = calculate_exam_performance(runs_data)
    class_score, class_total_points, class_eval, class_ident, class_breakdown = calculate_class_performance(runs_data, tasks_data, task_id_to_run_map)
    
    advisor_score, advisor_correct, advisor_eval, advisor_ident = calculate_advisor_tasks(runs_data)
    club_score, club_correct, club_eval, club_ident = calculate_club_activities(runs_data)
    resp_score, resp_correct, resp_eval, resp_ident = calculate_personal_responsibility(runs_data, tasks_data, task_id_to_run_map)
    
    daily_life_score = advisor_score + club_score + resp_score
    total_gpa = exam_score + class_score + daily_life_score
    
    return {
        "TotalStuGPA": total_gpa,
        "ExamPerformance": {"score": exam_score, "correct": exam_correct, "total_evaluated": exam_eval, "total_identified": exam_ident},
        "ClassPerformance": {
            "score": class_score, 
            "points": class_total_points, 
            "total_evaluated": class_eval, 
            "total_identified": class_ident,
            "breakdown": class_breakdown
        },
        "CampusDailyLife": {
            "score": daily_life_score,
            "AdvisorTask": {"score": advisor_score, "correct": advisor_correct, "total_evaluated": advisor_eval, "total_identified": advisor_ident},
            "ClubActivity": {"score": club_score, "correct": club_correct, "total_evaluated": club_eval, "total_identified": club_ident},
            "PersonalResponsibility": {"score": resp_score, "correct": resp_correct, "total_evaluated": resp_eval, "total_identified": resp_ident}
        }
    }

def calculate_hps(runs_data, tasks_data, task_id_to_run_map):
    total_hps = 0
    num_tasks_with_milestones = 0
    
    for task_def in tasks_data.values():
        if not task_def:
            continue
        task_id = task_def.get('task_id')
        if not task_id or task_id not in task_id_to_run_map:
            continue
        
        run = task_id_to_run_map[task_id]
        eval_record = run.get('evaluation_record', {})
        detail_dict = eval_record.get('detail_dict', {})
        
        total_sub_milestones = 0
        completed_sub_milestones = 0
        
        # 1. Location milestone
        required_place = task_def.get('require_place')
        if required_place:
            total_sub_milestones += 1
            final_location = detail_dict.get('final_location')
            if required_place == final_location:
                completed_sub_milestones += 1
        
        # 2. Task output milestone
        # As per require.md, ground_truth for comparison is in the *run* not the task def
        ground_truth = detail_dict.get('ground_truth')
        if ground_truth and isinstance(ground_truth, dict):
            task_output = detail_dict.get('task_output', {})
            
            num_gt_subtasks = len(ground_truth)
            total_sub_milestones += num_gt_subtasks
            
            if not detail_dict.get('failed_due_to_prerequisite', False):
                correct, _ = compare_outputs(ground_truth, task_output)
                completed_sub_milestones += correct
        
        if total_sub_milestones > 0:
            task_hps = completed_sub_milestones / total_sub_milestones
            total_hps += task_hps
            num_tasks_with_milestones += 1
            
    return total_hps / num_tasks_with_milestones if num_tasks_with_milestones > 0 else 0


def calculate_ltrr(runs_data, tasks_data, task_id_to_run_map):
    # LTRR tasks are defined as:
    # 1. Any task that has a corresponding '_trigger' task that was also run.
    # 2. All exam tasks.
    # 3. All semester 2 course selection tasks.

    run_task_ids = {get_task_id_from_sample_index(si) for si in runs_data.keys()}
    
    tasks_with_triggers = set()
    for task_id in run_task_ids:
        if not task_id.endswith('_trigger'):
             if f"{task_id}_trigger" in run_task_ids:
                 tasks_with_triggers.add(task_id)

    exam_task_ids = {get_task_id_from_sample_index(si) for si in runs_data if 'exam_' in si}
    
    course_selection_s2_task_ids = {get_task_id_from_sample_index(si) for si in runs_data if 'course_selection_s2' in si}

    ltrr_task_ids = tasks_with_triggers.union(exam_task_ids).union(course_selection_s2_task_ids)

    ltrr_runs = [task_id_to_run_map[task_id] for task_id in ltrr_task_ids if task_id in task_id_to_run_map]
    rate, correct, evaluated, identified = _calculate_accuracy_from_runs(ltrr_runs)
    return rate, correct, evaluated, identified


def calculate_pis(runs_data, tasks_data, task_id_to_run_map):
    # PIS tasks are defined as:
    # 1. Tasks with an empty instruction string.
    # 2. All "class tasks" (non-final_exam, non-triggered quiz questions).
    # 3. "Library Study" and "Advisor Assigned" tasks that have a trigger.

    instructionless_task_ids = {
        task.get('task_id') for task in tasks_data.values()
        if task and task.get('instruction') == ""
    }

    class_task_ids = {
        task.get('task_id') for task in tasks_data.values()
        if task and task.get('task_type') == 'quiz_question'
        and not task.get('is_trigger', False)
        and 'final_exam_' not in task.get('task_id', '')
    }
    
    # Identify triggered libstudy and advisor tasks from the actual runs
    run_task_ids = task_id_to_run_map.keys()
    triggered_lib_study_ids = set()
    triggered_advisor_ids = set()

    for task_id in run_task_ids:
        if not task_id.endswith('_trigger'):
            if f"{task_id}_trigger" in run_task_ids:
                if 'libstudy_task_' in task_id:
                    triggered_lib_study_ids.add(task_id)
                elif 'advisor_assigned_' in task_id:
                    triggered_advisor_ids.add(task_id)

    proactive_task_ids = instructionless_task_ids.union(class_task_ids).union(triggered_lib_study_ids).union(triggered_advisor_ids)
    
    proactive_runs = [task_id_to_run_map[task_id] for task_id in proactive_task_ids if task_id in task_id_to_run_map]
    rate, correct, evaluated, identified = _calculate_accuracy_from_runs(proactive_runs)
    return rate, correct, evaluated, identified

def process_experiment(experiment_dir, tasks_data, output_dir):
    print(f"Processing {experiment_dir}...")

    runs_file = Path(experiment_dir) / 'runs.json'
    metric_file = Path(experiment_dir) / 'metric.json'

    if not runs_file.exists() or not metric_file.exists():
        print(f"Skipping {experiment_dir}, missing runs.json or metric.json")
        return

    runs_data = {}
    print(f"Loading runs.json from {experiment_dir}...")
    with open(runs_file, 'r', encoding='utf-8') as f:
        try:
            runs_list = json.load(f)
            for run in tqdm(runs_list, desc=f"Processing runs from {experiment_dir}"):
                if 'sample_index' in run:
                    runs_data[run['sample_index']] = run
        except json.JSONDecodeError as e:
            print(f"Error decoding {runs_file}: {e}")
            return
    
    task_id_to_run_map = {get_task_id_from_sample_index(si): run for si, run in runs_data.items()}

    with open(metric_file, 'r', encoding='utf-8') as f:
        metric_data = json.load(f)

    # --- Categorize runs for sub-metric calculation ---
    task_defs_by_id = {task.get('task_id'): task for task in tasks_data.values() if task and 'task_id' in task}
    in_class_runs = []
    exam_runs_sub = [] # Renamed to avoid conflict with other 'exam_runs'
    daily_campus_runs = []

    for run in runs_data.values():
        task_id = get_task_id_from_sample_index(run.get('sample_index', ''))
        task_def = task_defs_by_id.get(task_id)

        is_quiz = task_def and task_def.get('task_type') == 'quiz_question'
        
        if is_quiz and 'exam_' in task_id:
            exam_runs_sub.append(run)
        elif is_quiz and 'exam_' not in task_id:
            in_class_runs.append(run)
        else:
            daily_campus_runs.append(run)

    results = {}
    results['StuGPA'] = calculate_stu_gpa(runs_data, tasks_data, task_id_to_run_map)
    results['SuccessRate'] = calculate_success_rate(runs_data)
    results['TurnAndTokenMetrics'] = calculate_turn_and_token_metrics(runs_data)
    results['HPS'] = calculate_hps(runs_data, tasks_data, task_id_to_run_map)
    
    ltrr_rate, ltrr_correct, ltrr_eval, ltrr_ident = calculate_ltrr(runs_data, tasks_data, task_id_to_run_map)
    results['LTRR'] = {"rate": ltrr_rate, "correct": ltrr_correct, "total_evaluated": ltrr_eval, "total_identified": ltrr_ident}
    
    pis_rate, pis_correct, pis_eval, pis_ident = calculate_pis(runs_data, tasks_data, task_id_to_run_map)
    results['PIS'] = {"rate": pis_rate, "correct": pis_correct, "total_evaluated": pis_eval, "total_identified": pis_ident}

    results['SubMetrics'] = {
        "InClass": calculate_category_metrics(in_class_runs),
        "Exam": calculate_category_metrics(exam_runs_sub),
        "DailyCampus": calculate_category_metrics(daily_campus_runs)
    }

    result_filename = Path(output_dir) / f"{Path(experiment_dir).name}_metrics.json"
    with open(result_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)

    print(f"Results for {experiment_dir} saved to {result_filename}")
    return results

def main():
    parser = argparse.ArgumentParser(description="Calculate metrics for experiment results.")
    parser.add_argument("--output_dir", type=str, default="output", help="Directory containing experiment subdirectories.")
    parser.add_argument("--tasks_file", type=str, default="task/tasks.json", help="Path to the tasks.json file.")
    parser.add_argument("--results_dir", type=str, default="results", help="Directory to save the calculated metrics.")
    args = parser.parse_args()

    Path(args.results_dir).mkdir(exist_ok=True)

    print(f"Loading tasks from {args.tasks_file}...")
    with open(args.tasks_file, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)
    print("Tasks loaded.")

    experiment_dirs = [d for d in Path(args.output_dir).iterdir() if d.is_dir()]
    
    all_results = {}
    for exp_dir in experiment_dirs:
        results = process_experiment(exp_dir, tasks_data, args.results_dir)
        all_results[exp_dir.name] = results

    # Create a summary CSV
    summary_data = []
    for exp_name, metrics in all_results.items():
        if metrics:
            summary_data.append({
                'Experiment': exp_name,
                'StuGPA': metrics['StuGPA']['TotalStuGPA'],
                'SuccessRate': metrics['SuccessRate'],
                'AvgTurns': metrics.get('TurnAndTokenMetrics', {}).get('avg_turns'),
                'MedianTurns': metrics.get('TurnAndTokenMetrics', {}).get('median_turns'),
                'MinTurns': metrics.get('TurnAndTokenMetrics', {}).get('min_turns'),
                'MaxTurns': metrics.get('TurnAndTokenMetrics', {}).get('max_turns'),
                'AvgTokens': metrics.get('TurnAndTokenMetrics', {}).get('avg_tokens'),
                'MedianTokens': metrics.get('TurnAndTokenMetrics', {}).get('median_tokens'),
                'MinTokens': metrics.get('TurnAndTokenMetrics', {}).get('min_tokens'),
                'MaxTokens': metrics.get('TurnAndTokenMetrics', {}).get('max_tokens'),
                'TotalTasks': metrics.get('TurnAndTokenMetrics', {}).get('total_task_count'),
                'InClass_SuccessRate': metrics.get('SubMetrics', {}).get('InClass', {}).get('success_rate'),
                'InClass_AvgTurns': metrics.get('SubMetrics', {}).get('InClass', {}).get('avg_turns'),
                'Exam_SuccessRate': metrics.get('SubMetrics', {}).get('Exam', {}).get('success_rate'),
                'Exam_AvgTurns': metrics.get('SubMetrics', {}).get('Exam', {}).get('avg_turns'),
                'DailyCampus_SuccessRate': metrics.get('SubMetrics', {}).get('DailyCampus', {}).get('success_rate'),
                'DailyCampus_AvgTurns': metrics.get('SubMetrics', {}).get('DailyCampus', {}).get('avg_turns'),
                'HPS': metrics.get('HPS', 'N/A'),
                'LTRR': metrics['LTRR']['rate'],
                'PIS': metrics['PIS']['rate'],
            })
    
    if summary_data:
        df = pd.DataFrame(summary_data)
        summary_csv_path = Path(args.results_dir) / 'summary.csv'
        df.to_csv(summary_csv_path, index=False)
        print(f"Summary of results saved to {summary_csv_path}")


if __name__ == "__main__":
    main()
