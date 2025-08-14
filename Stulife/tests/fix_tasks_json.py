import json
import os
from collections import defaultdict

def convert_task_format_no_dedupe(input_path: str, output_path: str):
    """
    Converts a task file from a JSON array to a JSON object keyed by a unique task_id.
    If task_ids are duplicated, a suffix is added to maintain uniqueness while preserving all tasks.

    Args:
        input_path: Path to the source JSON file (in array format).
        output_path: Path to the destination JSON file (in object/dict format).
    """
    print(f"Reading tasks from: {input_path}")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            tasks_array = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading JSON from {input_path}: {e}")
        return
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        return

    if not isinstance(tasks_array, list):
        print("Input file is not a JSON array. No conversion needed.")
        return

    print(f"Found {len(tasks_array)} tasks to process.")
    
    tasks_dict = {}
    id_counts = defaultdict(int)

    for i, task in enumerate(tasks_array):
        # Ensure every task has a base task_id
        if 'task_id' not in task or not task['task_id']:
            base_id = f"task_{i+1:04d}"
            task['task_id'] = base_id
        else:
            base_id = task['task_id']

        # Check if this base_id has been seen before
        if id_counts[base_id] > 0:
            # If it's a duplicate, create a new unique key
            new_key = f"{base_id}_{id_counts[base_id]}"
        else:
            # If it's the first time, use the base_id as the key
            new_key = base_id
        
        # Increment the count for this base_id
        id_counts[base_id] += 1
        
        # Add the task to the dictionary with the unique key
        tasks_dict[new_key] = task

    print(f"Writing {len(tasks_dict)} tasks to: {output_path} (duplicates handled)")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tasks_dict, f, indent=4, ensure_ascii=False)
        print("Conversion successful!")
    except Exception as e:
        print(f"Error writing to {output_path}: {e}")

if __name__ == "__main__":
    # Use the backup file as the source, and overwrite the main tasks.json
    source_file_path = os.path.join("任务数据", "tasks.json.backup")
    output_file_path = os.path.join("任务数据", "tasks.json")

    if os.path.exists(source_file_path):
        print("Starting conversion from backup file...")
        convert_task_format_no_dedupe(source_file_path, output_file_path)
    else:
        print(f"Source file {source_file_path} not found. Please ensure a backup exists.")
        # As a fallback, try to run on the primary file if backup is missing
        if os.path.exists(output_file_path):
             print(f"Attempting to run on {output_file_path} instead.")
             # We should back it up first to be safe
             temp_backup = f"{output_file_path}.temp_backup"
             os.rename(output_file_path, temp_backup)
             convert_task_format_no_dedupe(temp_backup, output_file_path)
             os.remove(temp_backup) # clean up temp
        else:
            print("No task file found to process.")

