"""
CampusTask - Main task controller for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import json
import re
from typing import Dict, Any, Optional, List, Union, Sequence
from pathlib import Path
from enum import Enum
import collections
import pickle

import sys
import os

# Add the src directory to the path if not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from tasks.task import Task, DatasetItem, AgentResponseParserResult, AgentAction
    from typings import Session, SessionEvaluationOutcome, MetricDict, SessionMetricCalculationPartial, Role, ChatHistoryItem, TaskName, SampleStatus
    from factories.chat_history_item import ChatHistoryItemFactory
except ImportError:
    try:
        from src.tasks.task import Task, DatasetItem, AgentResponseParserResult, AgentAction
        from src.typings import Session, SessionEvaluationOutcome, MetricDict, SessionMetricCalculationPartial, Role, ChatHistoryItem, TaskName, SampleStatus
        from src.factories.chat_history_item import ChatHistoryItemFactory
    except ImportError:
        from ...task import Task, DatasetItem, AgentResponseParserResult, AgentAction
        from ....typings import Session, SessionEvaluationOutcome, MetricDict, SessionMetricCalculationPartial, Role, ChatHistoryItem, TaskName, SampleStatus
        from ....factories.chat_history_item import ChatHistoryItemFactory

from .environment import CampusEnvironment
from .tools import ToolResult, ensure_english_message
from .systems.world_and_calendar import WorldTimeSystem
from .action_executor import ActionExecutor
from .system_prompt_generator import SystemPromptGenerator


class ContextInjectionState(Enum):
    """States for context injection state machine"""
    SYSTEM_PROMPT_SENT = "system_prompt_sent"
    DAILY_CONTEXT_NEEDED = "daily_context_needed"
    DAILY_CONTEXT_SENT = "daily_context_sent"
    TIME_CONTEXT_NEEDED = "time_context_needed"
    TIME_CONTEXT_SENT = "time_context_sent"
    LOCATION_VALIDATION_NEEDED = "location_validation_needed"
    TASK_CONTENT_READY = "task_content_ready"
    TASK_CONTENT_SENT = "task_content_sent"
    COMPLETED = "completed"


class CampusDatasetItem(DatasetItem):
    """Dataset item for campus life tasks"""

    task_id: str
    task_type: str
    is_trigger: bool = False
    instruction: str = ""
    require_time: Optional[str] = None
    require_place: Optional[str] = None
    source_building_id: Optional[str] = None
    world_state_change: List[Dict[str, Any]] = []
    details: Dict[str, Any] = {}
    ground_truth: Union[Dict[str, Any], str] = {}  # Can be dict for regular tasks or string for quiz questions
    available_systems: Optional[List[str]] = None  # New field for system availability
    require_sequence: bool = False  # Whether this task requires execution sequence validation
    require_precheck: bool = False  # Whether this task requires precheck for existing ground truth completion
    options: Optional[Dict[str, str]] = None  # Options for quiz questions
    pre_task_for: Optional[str] = None  # Comma-separated task IDs that this task is a prerequisite for
    
    def get_skill_list(self) -> List[str]:
        """Get skill list for this task"""
        # Map task types to skills
        skill_mapping = {
            "course_selection": ["planning", "decision_making"],
            "walking_simple": ["navigation", "spatial_reasoning"],
            "email_sending": ["communication", "text_composition"],
            "calendar_management": ["time_management", "scheduling"],
            "reservation": ["resource_management", "constraint_satisfaction"],
            "information_query": ["information_retrieval", "query_formulation"]
        }
        return skill_mapping.get(self.task_type, ["general"])
    
    def get_difficulty_level(self) -> int:
        """Get difficulty level for this task"""
        # Simple difficulty mapping based on task type
        difficulty_mapping = {
            "email_sending": 1,
            "walking_simple": 2,
            "information_query": 2,
            "calendar_management": 3,
            "reservation": 4,
            "course_selection": 5
        }
        return difficulty_mapping.get(self.task_type, 3)

    def get_available_systems(self) -> Optional[List[str]]:
        """Get list of available systems for this task"""
        return self.available_systems


class CampusTask(Task[CampusDatasetItem]):
    """
    Main task controller for CampusLifeBench
    Inherits from LAB Task class and implements campus-specific logic
    """
    
    def __init__(self, task_name: TaskName, chat_history_item_factory: ChatHistoryItemFactory, max_round: int = 10, data_dir: Optional[Union[Path, str]] = None):
        """
        Initialize CampusTask

        Args:
            task_name: Name of the task
            chat_history_item_factory: Factory for creating chat history items
            max_round: Maximum number of interaction rounds
            data_dir: Optional custom data directory for testing
        """
        super().__init__(task_name, chat_history_item_factory, max_round)

        # Initialize campus environment
        if isinstance(data_dir, str):
            data_dir = Path(data_dir)
            
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.campus_environment = CampusEnvironment(data_dir)
        self._data_dir = data_dir

        # Load task dataset
        self._load_dataset()

        # Track current simulation day for daily reset
        self._current_simulation_day: Optional[str] = None

        # Action executor will be initialized in _reset with available systems
        self.action_executor: Optional[ActionExecutor] = None

        # System prompt generator
        self.prompt_generator = SystemPromptGenerator()

        # Context injection state machine
        self.context_state: ContextInjectionState = ContextInjectionState.SYSTEM_PROMPT_SENT
        self.is_first_task_of_day: bool = True

        # Store current session for evaluation purposes
        self._current_session: Optional[Session] = None

        # Action execution history for sequence validation
        self.action_history: List[Dict[str, Any]] = []
        
        # Precheck failure tracking
        self.precheck_failed: bool = False
        self.precheck_failure_details: List[Dict[str, Any]] = []
        
        # Failed prerequisite task tracking
        # Key: failed task_id, Value: list of task_ids that are affected by this failure
        self.failed_prerequisite_tasks: Dict[str, List[str]] = {}

        # ADDED: Flag to ensure checkpoint is loaded only once
        self._checkpoint_loaded = False

    def _is_date_match(self, query_date: str, event_time: str) -> bool:
        """
        Check if a query date matches an event's time string, supporting week ranges.

        Args:
            query_date: Date to check (e.g., "Week 10, Monday")
            event_time: Event's time string (e.g., "Week 1-18, Monday, 14:00-16:50")

        Returns:
            True if the date matches, False otherwise.
        """
        try:
            # Parse query_date: "Week X, Day"
            query_match = re.match(r"Week (\d+), (\w+)", query_date, re.IGNORECASE)
            if not query_match:
                # Fallback for simple string containment for other formats
                return query_date in event_time

            query_week = int(query_match.group(1))
            query_day = query_match.group(2)

            # Parse event_time: "Week Y-Z, Day, ..." or "Week Y, Day, ..."
            event_parts = event_time.split(',')
            if len(event_parts) < 2:
                return query_date in event_time

            week_part = event_parts[0].strip()
            day_part = event_parts[1].strip()

            if query_day.lower() != day_part.lower():
                return False

            week_match = re.match(r"Week (\d+)\s*(?:-|to)\s*(\d+)", week_part, re.IGNORECASE)
            if week_match:
                # Week range
                start_week = int(week_match.group(1))
                end_week = int(week_match.group(2))
                return start_week <= query_week <= end_week
            else:
                week_match_single = re.match(r"Week (\d+)", week_part, re.IGNORECASE)
                if week_match_single:
                    event_week = int(week_match_single.group(1))
                    return query_week == event_week
                else:
                    return query_date in event_time
        except (ValueError, IndexError):
            return query_date in event_time

    def _get_available_systems(self, dataset_item: CampusDatasetItem) -> Optional[List[str]]:
        """
        Get available systems for the current task

        Args:
            dataset_item: Current dataset item

        Returns:
            List of available system names, or None for all systems
        """
        # Check if task specifies available systems
        if dataset_item.available_systems is not None:
            return dataset_item.available_systems

        # Default system availability based on task type
        task_type_defaults = {
            "email_sending": ["email"],
            "email_management": ["email"],
            "calendar_management": ["calendar"],
            "walking_simple": ["map", "geography"],
            "navigation": ["map", "geography"],
            "reservation": ["reservation", "map", "geography"],
            "information_query": ["bibliography", "data_system"],
            "course_selection": ["course_selection", "draft", "registration"],
            "quiz_question": [],  # Quiz questions don't need any systems
            "multi_system": None,  # All systems available
        }

        return task_type_defaults.get(dataset_item.task_type, None)
    
    def _load_dataset(self):
        """Load task dataset from JSON file"""
        # Try to load our E2E test tasks first
        e2e_dataset_path = self._data_dir / "e2e_test_tasks.json"
        dataset_path = self._data_dir / "tasks.json"

        try:
            # First try to load E2E test tasks
            if e2e_dataset_path.exists():
                with open(e2e_dataset_path, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                print(f"✅ Loaded E2E test tasks from {e2e_dataset_path}")
            else:
                # Fallback to standard tasks.json
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                print(f"✅ Loaded standard tasks from {dataset_path}")
        except FileNotFoundError:
            # Create minimal dataset if file doesn't exist
            tasks_data = {
                "sample_001": {
                    "task_id": "sample_001",
                    "task_type": "email_sending",
                    "is_trigger": False,
                    "instruction": "Send an email to your advisor asking about office hours.",
                    "require_time": None,
                    "require_place": None,
                    "source_building_id": None,
                    "world_state_change": [],
                    "details": {
                        "recipient": "advisor@university.edu",
                        "subject": "Office Hours Inquiry",
                        "body": "Dear Professor, I would like to know your office hours. Thank you."
                    },
                    "ground_truth": {
                        "recipient": "advisor@university.edu",
                        "subject": "Office Hours Inquiry",
                        "body": "Dear Professor, I would like to know your office hours. Thank you."
                    }
                }
            }
        
        # Convert to dataset items
        dataset = {}
        for sample_index, task_data in tasks_data.items():
            # Skip metadata entries
            if sample_index == "metadata":
                continue
            
            # Coerce boolean `require_time` and `require_place` to None to handle data inconsistencies
            if 'require_time' in task_data and isinstance(task_data.get('require_time'), bool):
                task_data['require_time'] = None
            if 'require_place' in task_data and isinstance(task_data.get('require_place'), bool):
                task_data['require_place'] = None
            
            # Preprocess 'options' field to handle nested dictionaries
            if 'options' in task_data and isinstance(task_data['options'], dict):
                new_options = {}
                for key, value in task_data['options'].items():
                    if isinstance(value, dict) and 'value' in value:
                        new_options[key] = str(value['value'])
                    elif isinstance(value, str):
                        new_options[key] = value
                task_data['options'] = new_options
            
            if task_data.get("ground_truth") is None:
                task_data["ground_truth"] = {}
                
            dataset[sample_index] = CampusDatasetItem(**task_data)

        self._set_dataset(dataset)
        print(f"✅ Loaded {len(dataset)} tasks into dataset")
    
    def _get_default_task_output(self) -> Dict[str, Optional[str]]:
        """Get default task output for failed tasks and trigger evaluation"""
        # This method is called when max_round is reached or other failures occur
        # We should trigger evaluation to assess the current task state
        try:
            # Use the stored current session to trigger evaluation
            if self._current_session is not None:
                # When the task limit is reached, we evaluate the final state.
                # _complete() will determine the outcome (CORRECT or INCORRECT)
                # based on the environment's state compared to the ground truth.
                self._complete(self._current_session)
        except Exception as e:
            # If the evaluation process itself fails, we log the error and
            # explicitly mark the task as FAILED and INCORRECT as a fallback.
            print(f"Warning: Evaluation failed in _get_default_task_output: {e}")
            if self._current_session:
                self._current_session.sample_status = SampleStatus.FAILED
                self._current_session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT

        return {"result": "Task failed or timed out"}
    
    @staticmethod
    def _parse_agent_response(agent_response: str) -> AgentResponseParserResult:
        """
        Parse agent response to extract ONLY THE FIRST action in Action: format or Answer: format for quiz questions
        This enforces single action execution per response.

        Args:
            agent_response: Raw agent response

        Returns:
            Parsed result with action and content (only first valid action found)
        """
        # First, extract content from <action> tags if present
        action_tag_pattern = r'<action>(.*?)</action>'
        action_tag_match = re.search(action_tag_pattern, agent_response, re.DOTALL | re.IGNORECASE)
        
        # Use content inside <action> tags if found, otherwise use the full response
        content_to_parse = action_tag_match.group(1).strip() if action_tag_match else agent_response
        
        # Look for Answer: pattern first (for quiz questions)
        answer_pattern = r'Answer:\s*([A-Za-z])\s*$'
        answer_match = re.search(answer_pattern, content_to_parse, re.MULTILINE | re.IGNORECASE)

        if answer_match:
            answer_letter = answer_match.group(1).upper()
            # Check if it's a valid letter (A-E)
            if answer_letter in ['A', 'B', 'C', 'D', 'E']:
                return AgentResponseParserResult(
                    action=AgentAction.FINISH,
                    content=f"Answer: {answer_letter}",
                    finish_reason="quiz_answer"
                )
            else:
                # Invalid letter
                return AgentResponseParserResult(
                    action=AgentAction.INVALID,
                    content=None,
                    finish_reason=f"Invalid answer letter '{answer_letter}'. Must be A, B, C, D, or E."
                )

        # Look for Action: pattern (for regular tasks)
        # Use balanced parentheses matching to handle nested parentheses correctly
        action_pattern = r'Action:\s*([^(]+)\((.*)\)$'
        # First try to match the entire line for better parsing
        lines = content_to_parse.strip().split('\n')
        action_match = None
        for line in lines:
            if line.strip().startswith('Action:'):
                action_match = re.search(action_pattern, line.strip(), re.DOTALL)
                if action_match:
                    break
        
        # Fallback to original pattern if line-by-line fails
        if not action_match:
            action_pattern = r'Action:\s*([^(]+)\((.*?)\)'
            action_match = re.search(action_pattern, content_to_parse, re.DOTALL | re.MULTILINE)

        if action_match:
            action_name = action_match.group(1).strip()
            action_params = action_match.group(2).strip()

            # Handle finish() action
            if action_name.lower() == 'finish':
                return AgentResponseParserResult(
                    action=AgentAction.FINISH,
                    content=None,
                    finish_reason=None
                )

            # Handle tool actions
            return AgentResponseParserResult(
                action=AgentAction.EXECUTE,
                content=f"{action_name}({action_params})",
                finish_reason=None
            )

        # Fallback: Look for finish keyword (backward compatibility)
        if re.search(r'\bfinish\s*\(\s*\)', content_to_parse, re.IGNORECASE):
            return AgentResponseParserResult(
                action=AgentAction.FINISH,
                content=None,
                finish_reason=None
            )

        # No valid action found
        return AgentResponseParserResult(
            action=AgentAction.INVALID,
            content=None,
            finish_reason="No valid action or answer found in response. Expected format: Action: tool_name(param1=\"value1\", param2=\"value2\") or Answer: [A-E]"
        )
    
    def _reset(self, session: Session) -> None:
        """
        Reset task state and implement context injection state machine

        Args:
            session: Current session
        """
        # ADDED: Load checkpoint state if this is the first task of the session run
        if not self._checkpoint_loaded and session.output_dir:
            self._load_checkpoint(session.output_dir)
            self._checkpoint_loaded = True

        # Store current session for evaluation purposes
        self._current_session = session
        current_item = self._get_current_dataset_item()

        # Reset precheck state for the new task
        self.precheck_failed = False
        self.precheck_failure_details.clear()

        # Check if this is a trigger task that should not participate in evaluation
        if current_item.is_trigger:
            print(f"🔔 Trigger task detected: {current_item.task_id}")
            # Mark trigger tasks for special handling
            if session.task_metadata is None:
                session.task_metadata = {}
            session.task_metadata['is_trigger_task'] = True
            session.task_metadata['skip_evaluation'] = True

        # Initialize action executor with available systems
        available_systems = self._get_available_systems(current_item)
        self.action_executor = ActionExecutor(self.campus_environment, available_systems)

        # Check if this is a new simulation day
        current_date = self._extract_date_from_task(current_item)
        date_for_logic = current_date or self._current_simulation_day
        
        if date_for_logic and date_for_logic != self._current_simulation_day:
            # Perform daily reset
            self.campus_environment.daily_reset(date_for_logic)
            self._current_simulation_day = date_for_logic
            self.is_first_task_of_day = True
        else:
            self.is_first_task_of_day = False

        # Apply world state changes
        if current_item.world_state_change:
            self.campus_environment.apply_world_state_changes(current_item.world_state_change)

        # Set initial location if specified
        if current_item.source_building_id:
            self.campus_environment.set_initial_location(current_item.source_building_id)

        # Initialize state machine
        self.context_state = ContextInjectionState.SYSTEM_PROMPT_SENT

        # Clear action history for new task
        self.action_history.clear()

        # Perform precheck if required
        self._perform_precheck(current_item)
        
        # If precheck failed, log the failure but continue with task execution
        if self.precheck_failed:
            print(f"⚠️ Precheck failed for task {current_item.task_id}: {len(self.precheck_failure_details)} ground truth condition(s) already satisfied")
            for detail in self.precheck_failure_details:
                print(f"   - {detail['system']}.{detail['component']}: {detail['description']}")

        # State 1: System Prompt & Tool Introduction
        system_prompt = self.prompt_generator.generate_prompt(available_systems)
        session.chat_history.inject(
            {"role": Role.USER, "content": system_prompt}
        )
        session.chat_history.inject(
            {"role": Role.AGENT, "content": "Understand."}
        )

        # Determine next state and inject ONLY the next required context
        if self.is_first_task_of_day:
            # Inject daily context with automatic agent acknowledgment
            current_date_for_prompt = self._current_simulation_day or "Week 1, Monday" # Fallback for absolute first task
            daily_message = f"Current date: {current_date_for_prompt}. Your current location: Lakeside Dormitory (B083)."
            session.chat_history.inject(
                {"role": Role.USER, "content": daily_message}
            )
            session.chat_history.inject(
                {"role": Role.AGENT, "content": "Understood."}
            )

            # Determine next state and inject next context immediately
            if current_item.require_time and not current_item.require_place:
                # For tasks that only require time, inject time, acknowledge, and provide instruction in one go
                time_message = self._get_full_time_string(current_item.require_time)
                full_time_message = f"Current time: {time_message}"
                session.chat_history.inject(
                    {"role": Role.USER, "content": full_time_message}
                )
                session.chat_history.inject(
                    {"role": Role.AGENT, "content": "Understood."}
                )
                
                self.context_state = ContextInjectionState.TASK_CONTENT_READY
                instruction_content = self._get_instruction_content(current_item)
                if instruction_content:
                    session.chat_history.inject(
                        {"role": Role.USER, "content": instruction_content}
                    )
                self.context_state = ContextInjectionState.TASK_CONTENT_SENT

            elif current_item.require_time: # This now implies require_place is true
                self.context_state = ContextInjectionState.TIME_CONTEXT_NEEDED
                time_message = self._get_full_time_string(current_item.require_time)
                full_time_message = f"Current time: {time_message}"
                session.chat_history.inject(
                    {"role": Role.USER, "content": full_time_message}
                )
            elif current_item.require_place:
                self.context_state = ContextInjectionState.LOCATION_VALIDATION_NEEDED
                time_message = self._get_full_time_string(current_item.require_time)
                full_time_message = f"Current time: {time_message}"
                session.chat_history.inject(
                    {"role": Role.USER, "content": full_time_message}
                )
            else:
                self.context_state = ContextInjectionState.TASK_CONTENT_READY
                instruction_content = self._get_instruction_content(current_item)
                # Only inject if there's actual content
                if instruction_content:
                    session.chat_history.inject(
                        {"role": Role.USER, "content": instruction_content}
                    )
                self.context_state = ContextInjectionState.TASK_CONTENT_SENT
        elif current_item.require_time and not current_item.require_place:
            # For tasks that only require time, inject time, acknowledge, and provide instruction in one go
            self.context_state = ContextInjectionState.TIME_CONTEXT_NEEDED
            time_message = self._get_full_time_string(current_item.require_time)
            full_time_message = f"Current time: {time_message}"
            session.chat_history.inject(
                {"role": Role.USER, "content": full_time_message}
            )
            session.chat_history.inject(
                {"role": Role.AGENT, "content": "Understood."}
            )
            
            self.context_state = ContextInjectionState.TASK_CONTENT_READY
            instruction_content = self._get_instruction_content(current_item)
            if instruction_content:
                session.chat_history.inject(
                    {"role": Role.USER, "content": instruction_content}
                )
            self.context_state = ContextInjectionState.TASK_CONTENT_SENT

        elif current_item.require_time: # This now implies require_place is true
            self.context_state = ContextInjectionState.TIME_CONTEXT_NEEDED
            # Inject time context and wait for agent response
            time_message = self._get_full_time_string(current_item.require_time)
            full_time_message = f"Current time: {time_message}"
            session.chat_history.inject(
                {"role": Role.USER, "content": full_time_message}
            )
        elif current_item.require_place:
            self.context_state = ContextInjectionState.LOCATION_VALIDATION_NEEDED
            # For location validation, we need time context first
            time_message = self._get_full_time_string(current_item.require_time)
            full_time_message = f"Current time: {time_message}"
            session.chat_history.inject(
                {"role": Role.USER, "content": full_time_message}
            )
        else:
            self.context_state = ContextInjectionState.TASK_CONTENT_READY
            # Inject task content and mark as sent
            instruction_content = self._get_instruction_content(current_item)
            # Only inject if there's actual content
            if instruction_content:
                session.chat_history.inject(
                    {"role": Role.USER, "content": instruction_content}
                )
            self.context_state = ContextInjectionState.TASK_CONTENT_SENT

        # Set task context for reservation system
        if hasattr(self.campus_environment.reservation_system, 'set_task_context'):
            task_context = {
                "task_id": current_item.task_id,
                "task_type": current_item.task_type,
                "details": current_item.details,
                "ground_truth": current_item.ground_truth,
                "target_date": current_date
            }
            self.campus_environment.reservation_system.set_task_context(task_context)
    
    def _extract_date_from_task(self, task_item: CampusDatasetItem) -> Optional[str]:
        """
        Extract simulation date from task data
        
        Args:
            task_item: Current task item
            
        Returns:
            Simulation date string or None
        """
        # Look for date in various places, with new priority order
        
        # 1. Try to extract from require_time using a more robust regex
        if task_item.require_time:
            try:
                # Match "Week X, Day" pattern, ignoring time.
                # This handles formats like "Week 0, Monday 10:00" and "Week 0, Monday, 10:00".
                match = re.match(r"(Week \d+,\s*\w+)", task_item.require_time)
                if match:
                    date_part = match.group(1)
                    return date_part
            except Exception:
                # If regex fails, fall through to the next method
                pass

        # 2. Fallback to target_date in details
        if "target_date" in task_item.details:
            return task_item.details["target_date"]
        
        # 3. Default to a simulation date
        return None

    def _get_full_time_string(self, time_str: str) -> str:
        """
        Get the full time string for a task.

        Args:
            time_str: Full time string like "Week 1, Tuesday,8:00" or "Week 1, Tuesday, 14:00"

        Returns:
            The original time string, or "Unknown time" if input is empty.
        """
        if not time_str:
            return "Unknown time"
        return time_str

    def _get_instruction_content(self, current_item: CampusDatasetItem) -> str:
        """
        Get appropriate instruction content, handling empty instructions for trigger tasks

        Args:
            current_item: Current dataset item

        Returns:
            Instruction content or time information for empty instructions
        """
        if not current_item.instruction or current_item.instruction.strip() == "":
            # For tasks with empty instruction but require_time, provide only time information
            if current_item.require_time:
                time_message = self._get_full_time_string(current_item.require_time)
                return f"Current time: {time_message}"
            else:
                # For empty instruction without time, return empty string to avoid injection
                return ""

        return current_item.instruction

    def _interact(self, session: Session) -> None:
        """
        Handle agent interaction using context injection state machine

        Args:
            session: Current session
        """
        # ADDED: Load checkpoint state if this is the first task of the session run
        if not self._checkpoint_loaded and session.output_dir:
            self._load_checkpoint(session.output_dir)
            self._checkpoint_loaded = True

        # Store current session for evaluation purposes
        self._current_session = session
        current_item = self._get_current_dataset_item()

        # Handle context injection states
        if self.context_state == ContextInjectionState.TIME_CONTEXT_NEEDED:
            self._handle_time_context_response(session, current_item)
            return
        elif self.context_state == ContextInjectionState.LOCATION_VALIDATION_NEEDED:
            self._handle_location_validation(session, current_item)
            return
        elif self.context_state == ContextInjectionState.TASK_CONTENT_READY:
            # Agent has reached correct location, provide task content
            instruction_content = self._get_instruction_content(current_item)
            # Only inject if there's actual content
            if instruction_content:
                session.chat_history.inject(
                    {"role": Role.USER, "content": instruction_content}
                )
            self.context_state = ContextInjectionState.TASK_CONTENT_SENT
            return

        # Handle task execution (after all context has been injected)
        if self.context_state == ContextInjectionState.TASK_CONTENT_SENT:
            self._handle_task_execution(session, current_item)
            return

    def _handle_time_context_response(self, session: Session, current_item: CampusDatasetItem) -> None:
        """Handle agent response to time context"""
        # Agent has acknowledged time context, determine next state
        if current_item.require_place:
            self.context_state = ContextInjectionState.LOCATION_VALIDATION_NEEDED
            # Only repeat time without location hint
            time_message = self._get_full_time_string(current_item.require_time)
            full_time_message = f"Current time: {time_message}"
            session.chat_history.inject(
                {"role": Role.USER, "content": full_time_message}
            )
        else:
            self.context_state = ContextInjectionState.TASK_CONTENT_READY
            # Inject task content
            instruction_content = self._get_instruction_content(current_item)
            # Only inject if there's actual content
            if instruction_content:
                session.chat_history.inject(
                    {"role": Role.USER, "content": instruction_content}
                )
            self.context_state = ContextInjectionState.TASK_CONTENT_SENT

    def _handle_location_validation(self, session: Session, current_item: CampusDatasetItem) -> None:
        """Handle location validation loop with enhanced logic"""
        current_location = self.campus_environment.get_current_location_for_validation()

        if current_location == current_item.require_place:
            # Location is correct, proceed to task content
            instruction_content = self._get_instruction_content(current_item)
            # Only inject if there's actual content
            if instruction_content:
                session.chat_history.inject(
                    {"role": Role.USER, "content": instruction_content}
                )
            self.context_state = ContextInjectionState.TASK_CONTENT_SENT
        else:
            # Location is incorrect - first try to parse and execute agent's action
            last_message = session.chat_history.get_item_deep_copy(-1)
            parsed_result = self._parse_agent_response(last_message.content)

            if parsed_result.action == AgentAction.EXECUTE:
                # Agent provided a valid action - execute it
                try:
                    if self.action_executor is None:
                        available_systems = self._get_available_systems(current_item)
                        self.action_executor = ActionExecutor(self.campus_environment, available_systems)

                    # Execute the action
                    tool_result = self.action_executor.execute_action(parsed_result.content)

                    # Record action execution for sequence validation
                    self._record_action_execution(parsed_result.content, tool_result)

                    # Add tool result to chat history as USER feedback
                    session.chat_history.inject(
                        {"role": Role.USER, "content": tool_result.message}
                    )

                    # Check location again after action execution
                    new_location = self.campus_environment.get_current_location_for_validation()
                    if new_location == current_item.require_place:
                        # Now at correct location, set state to provide task content in next round
                        self.context_state = ContextInjectionState.TASK_CONTENT_READY
                    # If still not at correct location, the tool result message is sufficient for this round
                    # Agent will try again in the next round

                except Exception as e:
                    # Execution error - provide as USER feedback
                    error_message = f"Action execution failed: {str(e)}"
                    session.chat_history.inject(
                        {"role": Role.USER, "content": error_message}
                    )
            elif parsed_result.action == AgentAction.FINISH:
                # Agent tried to finish without being at correct location.
                # Per user request, allow finish and trigger immediate evaluation.
                session.task_output = {"result": "Task finished prematurely by agent before reaching location"}
                session.sample_status = SampleStatus.COMPLETED
                self.context_state = ContextInjectionState.COMPLETED
                self._complete(session)
                return
            elif parsed_result.action == AgentAction.INVALID:
                # Invalid action - provide location hint and time
                time_message = self._get_full_time_string(current_item.require_time)
                full_time_message = f"Current time: {time_message}"
                session.chat_history.inject(
                    {"role": Role.USER, "content": full_time_message}
                )
            else:
                # No valid action found - provide location hint and time
                time_message = self._get_full_time_string(current_item.require_time)
                full_time_message = f"Current time: {time_message}"
                session.chat_history.inject(
                    {"role": Role.USER, "content": full_time_message}
                )
            # Stay in location validation state - agent needs to navigate


    def _handle_task_execution(self, session: Session, current_item: CampusDatasetItem) -> None:
        """Handle task execution after all context has been provided"""
        # Parse agent response
        last_message = session.chat_history.get_item_deep_copy(-1)
        parsed_result = self._parse_agent_response(last_message.content)

        if parsed_result.action == AgentAction.FINISH:
            # Agent finished the task - set proper completion status and evaluate
            session.task_output = {"result": "Task completed by agent"}
            session.sample_status = SampleStatus.COMPLETED
            self.context_state = ContextInjectionState.COMPLETED
            # Trigger evaluation
            self._complete(session)
            return

        elif parsed_result.action == AgentAction.EXECUTE:
            # Execute action using action executor
            try:
                if self.action_executor is None:
                    # Initialize action executor if not already done
                    available_systems = self._get_available_systems(current_item)
                    self.action_executor = ActionExecutor(self.campus_environment, available_systems)

                # Execute the action
                tool_result = self.action_executor.execute_action(parsed_result.content)

                # Record action execution for sequence validation
                self._record_action_execution(parsed_result.content, tool_result)

                # Add tool result to chat history as USER feedback
                session.chat_history.inject(
                    {"role": Role.USER, "content": tool_result.message}
                )

            except Exception as e:
                # Execution error - provide as USER feedback
                error_message = f"Action execution failed: {str(e)}"
                session.chat_history.inject(
                    {"role": Role.USER, "content": error_message}
                )

        else:
            # Invalid action - provide as USER feedback
            session.chat_history.inject(
                {"role": Role.USER, "content": "Invalid action. Please provide a valid Action."}
            )
    
    def _complete(self, session: Session) -> None:
        """
        Complete task and perform evaluation

        Args:
            session: Current session
        """
        current_item = self._get_current_dataset_item()

        # Skip evaluation for trigger tasks
        if current_item.is_trigger:
            print(f"🔔 Skipping evaluation for trigger task: {current_item.task_id}")
            # Set a special outcome to indicate this is a trigger task
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            session.evaluation_record.detail_dict = {
                "is_trigger_task": True,
                "skip_evaluation": True,
                "task_id": current_item.task_id
            }
            return

        # Check if current task is affected by failed prerequisite tasks
        affected_by_failed_prerequisite = self._check_affected_by_failed_prerequisite(current_item.task_id)
        if affected_by_failed_prerequisite:
            failed_prerequisite_task_id = affected_by_failed_prerequisite
            print(f"❌ Task {current_item.task_id} marked as INCORRECT due to failed prerequisite task: {failed_prerequisite_task_id}")
            session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            # Set task output and evaluation details
            session.task_output = {"result": "Set to incorrect due to the pre task"}
            if session.evaluation_record.detail_dict is None:
                session.evaluation_record.detail_dict = {}
            session.evaluation_record.detail_dict.update({
                "failed_due_to_prerequisite": True,
                "failed_prerequisite_task_id": failed_prerequisite_task_id,
                "error_reason": f"Task failed because prerequisite task '{failed_prerequisite_task_id}' failed"
            })
            self._enhance_evaluation_record(session, current_item)
            return

        # Check for precheck failure first
        if current_item.require_precheck and self.precheck_failed:
            print(f"❌ Task {current_item.task_id} marked as INCORRECT due to precheck failure")
            session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            # Enhance evaluation record with debug information including precheck details
            self._enhance_evaluation_record(session, current_item)
            return

        # Dispatch evaluation based on task type for non-trigger tasks
        if current_item.task_type == "email_sending":
            self._evaluate_email_sending(session, current_item)
        elif current_item.task_type == "course_selection":
            self._evaluate_course_selection(session, current_item)
        elif current_item.task_type == "walking_simple":
            self._evaluate_walking_simple(session, current_item)
        elif current_item.task_type == "calendar_management":
            self._evaluate_calendar_management(session, current_item)
        elif current_item.task_type == "reservation":
            self._evaluate_reservation(session, current_item)
        elif current_item.task_type == "quiz_question":
            self._evaluate_quiz_question(session, current_item)
        elif current_item.task_type == "multi_system":
            self._evaluate_multi_system(session, current_item)
        else:
            # Default evaluation
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            # Enhance evaluation record with debug information even for unknown task types
            self._enhance_evaluation_record(session, current_item)
        
        # Record failed prerequisite task if current task failed and has pre_task_for
        self._record_failed_prerequisite_task(session, current_item)
    
    def _evaluate_email_sending(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Evaluate email sending task"""
        try:
            # Get latest sent email
            latest_email = self.campus_environment.email_system.get_latest_email_for_evaluation()
            
            if not latest_email:
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            else:
                # Compare with ground truth
                gt = task_item.ground_truth
                
                # Unescape ground truth body for accurate comparison
                expected_body = gt.get("body", "").encode('latin1').decode('unicode_escape') if gt.get("body") else ""

                if (latest_email.recipient == gt.get("recipient") and
                    latest_email.subject == gt.get("subject") and
                    latest_email.body == expected_body):
                    session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
                else:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
                    
        except Exception:
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)
    
    def _save_course_selection_details(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Save course selection details for a given task"""
        if not session.output_dir:
            return

        try:
            # Get agent's draft schedule
            draft_schedule = self.campus_environment.course_selection_system.get_draft_schedule_for_evaluation()
            agent_selection = [s.__dict__ for s in draft_schedule.selected_sections]

            # Get course states for popularity info
            course_states = self.campus_environment.course_selection_system.get_course_states_for_evaluation()

            # Add popularity to agent selection
            for section in agent_selection:
                course_code = section.get("course_code")
                if course_code and course_code in course_states:
                    section["popularity"] = course_states[course_code].popularity_index

            # Get ground truth
            ground_truth = task_item.ground_truth.get("expected_schedule_outcome", {})
            if "selected_sections" in ground_truth:
                for section in ground_truth["selected_sections"]:
                    course_code = section.get("course_code")
                    if course_code and course_code in course_states:
                        section["popularity"] = course_states[course_code].popularity_index
            
            # Prepare data to save
            output_data = {
                "task_id": task_item.task_id,
                "ground_truth": ground_truth,
                "agent_selection": agent_selection
            }
            
            # Define output path
            output_path = Path(session.output_dir) / "course_selection_eval"
            output_path.mkdir(parents=True, exist_ok=True)
            file_path = output_path / f"{task_item.task_id}.json"
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Failed to save course selection details for task {task_item.task_id}: {e}")

    def _evaluate_course_selection(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Evaluate course selection task"""
        self._save_course_selection_details(session, task_item)
        try:
            # Get current draft schedule
            draft_schedule = self.campus_environment.course_selection_system.get_draft_schedule_for_evaluation()
            expected_outcome = task_item.ground_truth.get("expected_schedule_outcome", {})
            expected_sections = expected_outcome.get("selected_sections", [])
            
            # Compare draft schedule with expected outcome
            if len(draft_schedule.selected_sections) != len(expected_sections):
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            else:
                # Check each course and pass assignment
                all_found = True
                for expected in expected_sections:
                    found = False
                    for actual in draft_schedule.selected_sections:
                        if (actual.course_code == expected["course_code"] and
                            actual.assigned_pass == expected["assigned_pass"]):
                            found = True
                            break
                    if not found:
                        all_found = False
                        break
                
                session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT if all_found else SessionEvaluationOutcome.INCORRECT
            
        except Exception:
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)
    
    def _evaluate_walking_simple(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Evaluate simple walking task by strictly checking the path taken."""
        try:
            # Get geography state for evaluation
            geo_state = self.campus_environment.geography_system.get_state_for_evaluation()
            
            # Get expected path from ground truth
            expected_path = task_item.ground_truth.get("path_taken")

            # If there's no expected path in ground_truth, fallback to original simple check
            if not expected_path:
                expected_outcome = task_item.ground_truth.get("expected_outcome", {})
                target_location = expected_outcome.get("target_location_id")
                if target_location and geo_state.current_location_id == target_location:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
                else:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            else:
                # Construct the full path taken by the agent from walk_history
                agent_path = []
                if geo_state.walk_history:
                    # Start with the first segment
                    agent_path.extend(geo_state.walk_history[0])
                    # Append subsequent segments, avoiding overlapping points
                    for segment in geo_state.walk_history[1:]:
                        if agent_path and segment and agent_path[-1] == segment[0]:
                            agent_path.extend(segment[1:])
                        else:
                            # Handle cases of disjointed paths if necessary, for now, just append
                            agent_path.extend(segment)
                
                # Check if the agent's path exactly matches the expected path
                if agent_path == expected_path:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
                else:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
                    # Initialize detail_dict if it doesn't exist for additional debugging info
                    if session.evaluation_record.detail_dict is None:
                        session.evaluation_record.detail_dict = {}
                    session.evaluation_record.detail_dict.update({
                        "error_reason": "Path taken does not match expected path.",
                        "expected_path": expected_path,
                        "agent_path": agent_path
                    })
                
        except Exception as e:
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            if session.evaluation_record.detail_dict is None:
                session.evaluation_record.detail_dict = {}
            session.evaluation_record.detail_dict["error"] = str(e)
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)
    
    def _evaluate_calendar_management(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Evaluate calendar management task"""
        try:
            # Get calendar events for the specified calendar
            calendar_id = task_item.details.get("calendar_id", "self")
            events = self.campus_environment.calendar_system.get_calendar_events_for_evaluation(calendar_id)
            
            # Check if expected event was created
            expected_details = task_item.details
            event_found = False
            for event in events:
                time_match = self._is_date_match(expected_details.get("time"), event.time)
                if (event.event_title == expected_details.get("event_title") and
                    event.location == expected_details.get("location") and
                    time_match):
                    event_found = True
                    break
            
            session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT if event_found else SessionEvaluationOutcome.INCORRECT
            
        except Exception:
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)
    
    def _evaluate_reservation(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Evaluate reservation task"""
        try:
            # Get reservations made by this task
            reservations = self.campus_environment.reservation_system.get_reservations_for_evaluation(task_item.task_id)
            
            if not reservations:
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            else:
                # Handle both flat and nested ground truth structures
                expected_outcomes = []
                if "expected_reservation_outcome" in task_item.ground_truth:
                    expected_outcomes = task_item.ground_truth["expected_reservation_outcome"]
                elif isinstance(task_item.ground_truth, dict) and "location_id" in task_item.ground_truth:
                    # Handle flat structure by wrapping it in a list
                    expected_outcomes = [task_item.ground_truth]

                if not expected_outcomes:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
                    self._enhance_evaluation_record(session, task_item)
                    return

                reservation_matched = False
                for reservation in reservations:
                    for expected in expected_outcomes:
                        # Stricter validation using AND logic with comprehensive field checks
                        # Using getattr for reservation object and .get for expected dict for safety
                        seat_id_match = ("seat_id" not in expected or
                                       getattr(reservation, 'seat_id', None) == expected.get("seat_id"))

                        item_name_match = ("item_name" not in expected or
                                         getattr(reservation, 'item_name', None) == expected.get("item_name"))
                        
                        location_id_match = ("location_id" not in expected or
                                           getattr(reservation, 'location_id', None) == expected.get("location_id"))

                        time_slot_match = ("time_slot" not in expected or
                                         getattr(reservation, 'time_slot', None) == expected.get("time_slot"))

                        date_match = ("date" not in expected or
                                    getattr(reservation, 'date', None) == expected.get("date"))

                        if seat_id_match and item_name_match and location_id_match and time_slot_match and date_match:
                            # A reservation matches all specified criteria in an expected outcome
                            reservation_matched = True
                            break
                    if reservation_matched:
                        break
                
                session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT if reservation_matched else SessionEvaluationOutcome.INCORRECT
            
        except Exception:
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)

    def _evaluate_quiz_question(self, session: Session, task_item: CampusDatasetItem) -> None:
        """Evaluate quiz question task"""
        try:
            # Get the last agent response
            last_message = session.chat_history.get_item_deep_copy(-1)
            parsed_result = self._parse_agent_response(last_message.content)

            # Check if agent provided an answer
            if parsed_result.action == AgentAction.FINISH and parsed_result.finish_reason == "quiz_answer":
                # Extract the answer from the content
                agent_answer = parsed_result.content.replace("Answer: ", "").strip().upper()
                correct_answer = task_item.ground_truth.upper()

                # Check if the answer is correct
                if agent_answer == correct_answer:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
                else:
                    session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
            else:
                # Agent didn't provide a valid answer format
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT

        except Exception:
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)

    def _evaluate_multi_system(self, session: Session, task_item: CampusDatasetItem) -> None:
        """
        Evaluate multi-system tasks that involve multiple campus systems
        Uses AND logic: ALL components must be correct for CORRECT outcome
        """
        try:
            ground_truth = task_item.ground_truth
            if not isinstance(ground_truth, dict):
                session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
                return

            # Group criteria by system type based on key prefixes
            grouped_criteria = collections.defaultdict(list)
            
            # Map legacy keys and new prefixes to a canonical system type
            SYSTEM_PREFIX_MAP = {
                "email_sent": "email",
                "email": "email",
                "reservation_made": "reservation",
                "reservation": "reservation",
                "calendar_event": "calendar",
                "calendar": "calendar",
                "location_reached": "geography",
                "location": "geography",
                "course_selected": "course",
                "course": "course",
                "walk_to": "walk_to",
                "walk": "walk_to",
            }

            for key, criteria in ground_truth.items():
                prefix = key.split('_')[0]
                
                system_type = None
                if key in SYSTEM_PREFIX_MAP: # Handle legacy full keys first
                    system_type = SYSTEM_PREFIX_MAP[key]
                elif prefix in SYSTEM_PREFIX_MAP: # Handle prefixes like "email" or "reservation"
                    system_type = SYSTEM_PREFIX_MAP[prefix]

                if system_type:
                    # Criteria for a legacy key could be a single dict or a list of dicts
                    if isinstance(criteria, list):
                        grouped_criteria[system_type].extend(criteria)
                    else:
                        grouped_criteria[system_type].append(criteria)

            all_components_correct = True

            # Evaluate each system component that has criteria
            if "email" in grouped_criteria:
                if not self._evaluate_email_component(grouped_criteria["email"]):
                    all_components_correct = False

            if "reservation" in grouped_criteria:
                if not self._evaluate_reservation_component(grouped_criteria["reservation"], task_item.task_id):
                    all_components_correct = False

            if "calendar" in grouped_criteria:
                if not self._evaluate_calendar_component(grouped_criteria["calendar"]):
                    all_components_correct = False

            if "geography" in grouped_criteria:
                if not self._evaluate_geography_component(grouped_criteria["geography"]):
                    all_components_correct = False

            if "walk_to" in grouped_criteria:
                if not self._evaluate_walk_to_component(grouped_criteria["walk_to"]):
                    all_components_correct = False

            if "course" in grouped_criteria:
                if not self._evaluate_course_component(session, task_item, grouped_criteria["course"]):
                    all_components_correct = False

            # Validate execution sequence for multi-system tasks
            sequence_valid = True
            sequence_message = "No sequence validation performed"

            if all_components_correct and task_item.require_sequence:
                # Only validate sequence if all components are correct and sequence validation is required
                sequence_valid, sequence_message = self._validate_execution_sequence(ground_truth)
                if not sequence_valid:
                    print(f"Sequence validation failed: {sequence_message}")
                else:
                    print(f"Sequence validation passed: {sequence_message}")
            elif task_item.require_sequence:
                # If sequence validation is required but components failed, note this
                sequence_message = "Sequence validation skipped due to component failures"

            # Set final outcome based on AND logic (components + sequence)
            if all_components_correct and sequence_valid:
                session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
            else:
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
                if not sequence_valid:
                    # Store sequence validation failure information
                    if session.evaluation_record.detail_dict is None:
                        session.evaluation_record.detail_dict = {}
                    session.evaluation_record.detail_dict['sequence_validation_error'] = sequence_message

        except Exception as e:
            print(f"Error in multi-system evaluation: {e}")
            session.evaluation_record.outcome = SessionEvaluationOutcome.UNKNOWN
            
        # Enhance evaluation record with debug information
        self._enhance_evaluation_record(session, task_item)

    def _evaluate_email_component(self, email_criteria_list: List[dict]) -> bool:
        """
        Evaluate email component for multi-system tasks.
        Checks if for every criterion in the list, a unique matching sent email is found.
        """
        try:
            # ASSUMPTION: The email system provides a method to get all sent emails for evaluation.
            # The previous `get_latest_email_for_evaluation` is insufficient for multiple email tasks.
            # We will assume a method like `get_all_emails_for_evaluation` or access to a `sent_emails` list.
            if not hasattr(self.campus_environment.email_system, 'get_all_emails_for_evaluation'):
                 print("Warning: Email system does not support fetching all emails. Evaluation may be incorrect.")
                 # Fallback to legacy behavior for single email check
                 if len(email_criteria_list) == 1:
                     latest_email = self.campus_environment.email_system.get_latest_email_for_evaluation()
                     if latest_email:
                         return self._email_matches_criteria(latest_email, email_criteria_list[0])
                 return False

            sent_emails = self.campus_environment.email_system.get_all_emails_for_evaluation()
            
            if len(sent_emails) < len(email_criteria_list):
                return False

            matched_emails = [False] * len(sent_emails)

            for criteria in email_criteria_list:
                found_match_for_criteria = False
                for i, email in enumerate(sent_emails):
                    if matched_emails[i]:
                        continue  # This email has already been matched

                    if self._email_matches_criteria(email, criteria):
                        matched_emails[i] = True
                        found_match_for_criteria = True
                        break
                
                if not found_match_for_criteria:
                    return False  # No unique match found for this criterion

            return True  # All criteria were satisfied by unique emails

        except Exception:
            return False

    def _email_matches_criteria(self, email: Any, criteria: dict) -> bool:
        """Helper to check if a single email object matches given criteria."""
        # Handle SentEmail object (use dot notation) and fallback for dict-like structure
        email_to = getattr(email, 'to', getattr(email, 'recipient', email.get("to", "")))
        email_subject = getattr(email, 'subject', email.get("subject", ""))
        email_body = getattr(email, 'body', email.get("body", ""))

        # Check recipient
        if "recipient" in criteria and email_to != criteria["recipient"]:
            return False
        if "recipient_contains" in criteria and criteria["recipient_contains"].lower() not in email_to.lower():
            return False

        # Check subject
        if "subject_contains" in criteria and criteria["subject_contains"].lower() not in email_subject.lower():
            return False

        # Check body
        if "body_contains" in criteria:
            # Unescape all escape sequences from ground truth string before comparison
            expected_body = criteria["body_contains"].encode('latin1').decode('unicode_escape')
            if expected_body.lower() not in email_body.lower():
                return False
            
        return True

    def _evaluate_reservation_component(self, reservation_criteria_list: List[dict], task_id: str) -> bool:
        """
        Evaluate reservation component for multi-system tasks.
        Checks if for every criterion in the list, a unique matching reservation is found.
        """
        try:
            reservations = self.campus_environment.reservation_system.get_reservations_for_evaluation(task_id)
            if len(reservations) < len(reservation_criteria_list):
                return False

            matched_reservations = [False] * len(reservations)

            for criteria in reservation_criteria_list:
                found_match_for_criteria = False
                for i, reservation in enumerate(reservations):
                    if matched_reservations[i]:
                        continue

                    if self._reservation_matches_criteria(reservation, criteria):
                        matched_reservations[i] = True
                        found_match_for_criteria = True
                        break

                if not found_match_for_criteria:
                    return False
            
            return True

        except Exception:
            return False

    def _reservation_matches_criteria(self, reservation: Any, criteria: dict) -> bool:
        """Helper to check if a single reservation object matches given criteria."""
        seat_id_match = ("seat_id" not in criteria or
                           getattr(reservation, 'seat_id', None) == criteria["seat_id"])
        item_name_match = ("item_name" not in criteria or
                           getattr(reservation, 'item_name', None) == criteria["item_name"])
        location_id_match = ("location_id" not in criteria or
                             getattr(reservation, 'location_id', None) == criteria["location_id"])
        time_match = ("time" not in criteria or
                      getattr(reservation, 'time_slot', None) == criteria["time"])
        date_match = ("date" not in criteria or
                      getattr(reservation, 'date', None) == criteria["date"])

        return seat_id_match and item_name_match and location_id_match and time_match and date_match

    def _evaluate_calendar_component(self, calendar_criteria_list: List[dict]) -> bool:
        """
        Evaluate calendar component for multi-system tasks.
        Checks if for every criterion in the list, a unique matching calendar event is found.
        """
        try:
            # Assumption: All criteria are for the same calendar.
            # Fetch calendar_id from the first criterion if specified.
            calendar_id = calendar_criteria_list[0].get("calendar_id", "self") if calendar_criteria_list else "self"
            events = self.campus_environment.calendar_system.get_calendar_events_for_evaluation(calendar_id)
            
            if len(events) < len(calendar_criteria_list):
                return False

            matched_events = [False] * len(events)

            for criteria in calendar_criteria_list:
                found_match_for_criteria = False
                for i, event in enumerate(events):
                    if matched_events[i]:
                        continue
                    
                    if self._calendar_event_matches_criteria(event, criteria):
                        matched_events[i] = True
                        found_match_for_criteria = True
                        break
                
                if not found_match_for_criteria:
                    return False
            
            return True

        except Exception:
            return False

    def _calendar_event_matches_criteria(self, event: Any, criteria: dict) -> bool:
        """Helper to check if a single calendar event matches given criteria."""
        matches = True
        # Check event title contains specified text
        if "event_title_contains" in criteria:
            expected_title = criteria["event_title_contains"].encode('latin1').decode('unicode_escape')
            if expected_title.lower() not in event.event_title.lower():
                matches = False
        # Check exact time match
        if "time" in criteria and event.time != criteria["time"]:
            matches = False
        # Check exact location match
        if "location" in criteria:
            expected_location = criteria["location"].encode('latin1').decode('unicode_escape')
            if event.location != expected_location:
                matches = False
        # Legacy support
        if "title_contains" in criteria:
            expected_title_legacy = criteria["title_contains"].encode('latin1').decode('unicode_escape')
            if expected_title_legacy.lower() not in event.event_title.lower():
                matches = False
        if "date" in criteria and event.time != criteria["date"]:
            matches = False
        return matches

    def _evaluate_geography_component(self, geography_criteria_list: List[dict]) -> bool:
        """
        Evaluate geography component for multi-system tasks.
        Checks if the final geography state satisfies ALL criteria in the list.
        """
        try:
            geo_state = self.campus_environment.geography_system.get_state_for_evaluation()

            for criteria in geography_criteria_list:
                # Check current location if specified
                if "current_location" in criteria:
                    current_loc = geo_state.get("current_location") if isinstance(geo_state, dict) else getattr(geo_state, 'current_location_id', None)
                    if current_loc != criteria["current_location"]:
                        return False
                # Check visited locations if specified
                if "visited_locations" in criteria:
                    visited = geo_state.get("visited_locations", []) if isinstance(geo_state, dict) else getattr(geo_state, 'visited_locations', [])
                    required = criteria["visited_locations"]
                    if not all(loc in visited for loc in required):
                        return False
            
            return True

        except Exception:
            return False

    def _evaluate_course_component(self, session: Session, task_item: CampusDatasetItem, course_criteria_list: List[dict]) -> bool:
        """
        Evaluate course selection component for multi-system tasks.
        Checks if for every criterion in the list, a unique matching course selection is found.
        """
        self._save_course_selection_details(session, task_item)
        try:
            draft_schedule = self.campus_environment.course_selection_system.get_draft_schedule_for_evaluation()
            selected_sections = draft_schedule.selected_sections

            if len(selected_sections) < len(course_criteria_list):
                return False

            matched_sections = [False] * len(selected_sections)

            for criteria in course_criteria_list:
                found_match_for_criteria = False
                for i, section in enumerate(selected_sections):
                    if matched_sections[i]:
                        continue
                    
                    # Check course code
                    if "course_code" in criteria and section.course_code == criteria["course_code"]:
                        # Check pass assignment if specified
                        if "assigned_pass" in criteria and section.assigned_pass != criteria["assigned_pass"]:
                            continue # Pass assignment doesn't match, this is not the right section
                        
                        # Match found
                        matched_sections[i] = True
                        found_match_for_criteria = True
                        break
                
                if not found_match_for_criteria:
                    return False
            
            return True

        except Exception:
            return False

    def _evaluate_walk_to_component(self, walk_to_criteria_list: List[dict]) -> bool:
        """
        Evaluate walk_to component for multi-system tasks.
        Checks if the final location matches the target_location_id.
        """
        try:
            geo_state = self.campus_environment.geography_system.get_state_for_evaluation()
            current_location = geo_state.current_location_id

            for criteria in walk_to_criteria_list:
                if "target_location_id" in criteria:
                    if current_location != criteria["target_location_id"]:
                        return False
            
            return True

        except Exception:
            return False

    def _release(self) -> None:
        """Release resources"""
        pass
    
    def calculate_metric(self, session_partial_list: Sequence[SessionMetricCalculationPartial]) -> MetricDict:
        """Calculate metrics for the task, filtering out trigger tasks"""
        # Filter out trigger tasks from metric calculation
        filtered_session_list = []
        trigger_task_count = 0

        for session_partial in session_partial_list:
            # Get the dataset item to check if it's a trigger task
            # We need to access the dataset directly since __get_dataset_item is private
            assert self._Task__dataset is not None
            dataset_item = self._Task__dataset[session_partial.sample_index]
            if dataset_item.is_trigger:
                trigger_task_count += 1
                print(f"🔔 Excluding trigger task from metrics: {dataset_item.task_id}")
                continue
            filtered_session_list.append(session_partial)

        print(f"📊 Metric calculation: {len(filtered_session_list)} regular tasks, {trigger_task_count} trigger tasks excluded")

        # Calculate metrics only for non-trigger tasks
        if not filtered_session_list:
            # If all tasks are trigger tasks, return empty metrics
            return {
                "overall": {
                    "basic": {"session_count": 0.0},
                    "evaluation_outcome": {},
                    "sample_status": {}
                },
                "trigger_info": {
                    "total_trigger_tasks": float(trigger_task_count),
                    "regular_tasks_evaluated": 0.0
                }
            }

        # Use the base class method for filtered sessions
        base_metrics = self._calculate_overall_metric(filtered_session_list)

        # Add trigger task information to metrics
        base_metrics["trigger_info"] = {
            "total_trigger_tasks": float(trigger_task_count),
            "regular_tasks_evaluated": float(len(filtered_session_list))
        }

        # Wrap in overall structure to match expected format
        return {
            "overall": base_metrics,
            "trigger_info": base_metrics["trigger_info"]
        }

    def _record_action_execution(self, action_content: str, tool_result: ToolResult) -> None:
        """
        Record action execution for sequence validation

        Args:
            action_content: The action content that was executed
            tool_result: The result of the action execution
        """
        import time

        # Extract system type from action content
        system_type = self._extract_system_type_from_action(action_content)

        # Record the action with timestamp
        action_record = {
            "timestamp": time.time(),
            "system_type": system_type,
            "action_content": action_content,
            "success": tool_result.is_success(),
            "message": tool_result.message
        }

        self.action_history.append(action_record)

    def _perform_precheck(self, task_item: CampusDatasetItem) -> None:
        """
        Perform precheck to verify if any ground truth conditions are already satisfied
        before task execution begins.
        
        Args:
            task_item: Current task item to check against
        """
        if not task_item.require_precheck:
            return
            
        ground_truth = task_item.ground_truth
        if not isinstance(ground_truth, dict):
            return
            
        import time
        current_timestamp = time.time()
        
        # Check email system if ground truth contains email requirements
        if task_item.task_type == "email_sending" or "email_sent" in ground_truth:
            self._check_email_precheck(ground_truth, current_timestamp)
            
        # Check reservation system if ground truth contains reservation requirements  
        if task_item.task_type == "reservation" or "reservation_made" in ground_truth:
            self._check_reservation_precheck(ground_truth, task_item.task_id, current_timestamp)
            
        # Check calendar system if ground truth contains calendar requirements
        if task_item.task_type == "calendar_management" or "calendar_event" in ground_truth:
            self._check_calendar_precheck(ground_truth, current_timestamp)
            
        # Check course selection system if ground truth contains course requirements
        if task_item.task_type == "course_selection" or "course_selected" in ground_truth:
            self._check_course_selection_precheck(ground_truth, current_timestamp)
            
        # Check geography system if ground truth contains location requirements
        if task_item.task_type == "walking_simple" or "location_reached" in ground_truth:
            self._check_geography_precheck(ground_truth, current_timestamp)
    
    def _check_email_precheck(self, ground_truth: dict, timestamp: float) -> None:
        """Check if email requirements are already satisfied"""
        try:
            latest_email = self.campus_environment.email_system.get_latest_email_for_evaluation()
            if latest_email is None:
                return
                
            # Check for email_sending task type ground truth
            if "recipient" in ground_truth:
                if (hasattr(latest_email, 'to') and latest_email.to == ground_truth["recipient"]) or \
                   (hasattr(latest_email, 'recipient') and latest_email.recipient == ground_truth["recipient"]):
                    self.precheck_failed = True
                    self.precheck_failure_details.append({
                        "system": "email",
                        "component": "recipient",
                        "expected": ground_truth["recipient"],
                        "found": getattr(latest_email, 'to', getattr(latest_email, 'recipient', None)),
                        "timestamp": timestamp,
                        "description": f"Email recipient '{ground_truth['recipient']}' already satisfied before task execution"
                    })
                    
            # Check for multi-system task email_sent component
            elif "email_sent" in ground_truth:
                email_criteria = ground_truth["email_sent"]
                if "recipient" in email_criteria:
                    if (hasattr(latest_email, 'to') and latest_email.to == email_criteria["recipient"]) or \
                       (hasattr(latest_email, 'recipient') and latest_email.recipient == email_criteria["recipient"]):
                        self.precheck_failed = True
                        self.precheck_failure_details.append({
                            "system": "email",
                            "component": "email_sent.recipient",
                            "expected": email_criteria["recipient"],
                            "found": getattr(latest_email, 'to', getattr(latest_email, 'recipient', None)),
                            "timestamp": timestamp,
                            "description": f"Email recipient '{email_criteria['recipient']}' already satisfied before task execution"
                        })
        except Exception as e:
            print(f"Warning: Email precheck failed: {e}")
    
    def _check_reservation_precheck(self, ground_truth: dict, task_id: str, timestamp: float) -> None:
        """Check if reservation requirements are already satisfied"""
        try:
            reservations = self.campus_environment.reservation_system.get_reservations_for_evaluation(task_id)
            if not reservations:
                return
                
            # Check for reservation task type ground truth
            if "expected_reservation_outcome" in ground_truth:
                expected_outcomes = ground_truth["expected_reservation_outcome"]
                for reservation in reservations:
                    for expected in expected_outcomes:
                        if ("seat_id" in expected and getattr(reservation, 'seat_id', reservation.get('seat_id') if isinstance(reservation, dict) else None) == expected["seat_id"]) or \
                           ("item_name" in expected and getattr(reservation, 'item_name', reservation.get('item_name') if isinstance(reservation, dict) else None) == expected["item_name"]):
                            self.precheck_failed = True
                            self.precheck_failure_details.append({
                                "system": "reservation",
                                "component": "expected_reservation_outcome",
                                "expected": expected,
                                "found": reservation.__dict__ if hasattr(reservation, '__dict__') else reservation,
                                "timestamp": timestamp,
                                "description": f"Reservation already satisfied before task execution"
                            })
                            
            # Check for multi-system task reservation_made component
            elif "reservation_made" in ground_truth:
                reservation_criteria = ground_truth["reservation_made"]
                for reservation in reservations:
                    matches = True
                    if "item_name" in reservation_criteria and getattr(reservation, 'item_name', reservation.get('item_name') if isinstance(reservation, dict) else None) != reservation_criteria["item_name"]:
                        matches = False
                    if "location_id" in reservation_criteria and getattr(reservation, 'location_id', reservation.get('location_id') if isinstance(reservation, dict) else None) != reservation_criteria["location_id"]:
                        matches = False
                    if matches:
                        self.precheck_failed = True
                        self.precheck_failure_details.append({
                            "system": "reservation",
                            "component": "reservation_made",
                            "expected": reservation_criteria,
                            "found": reservation.__dict__ if hasattr(reservation, '__dict__') else reservation,
                            "timestamp": timestamp,
                            "description": f"Reservation already satisfied before task execution"
                        })
                        break
        except Exception as e:
            print(f"Warning: Reservation precheck failed: {e}")
    
    def _check_calendar_precheck(self, ground_truth: dict, timestamp: float) -> None:
        """Check if calendar requirements are already satisfied"""
        try:
            calendar_id = "self"  # Default calendar
            if "calendar_event" in ground_truth:
                calendar_id = ground_truth["calendar_event"].get("calendar_id", "self")
                
            events = self.campus_environment.calendar_system.get_calendar_events_for_evaluation(calendar_id)
            
            # Check for calendar_management task type ground truth
            if "event_title" in ground_truth:
                for event in events:
                    if (event.event_title == ground_truth.get("event_title") and
                        event.location == ground_truth.get("location") and
                        event.time == ground_truth.get("time")):
                        self.precheck_failed = True
                        self.precheck_failure_details.append({
                            "system": "calendar",
                            "component": "event",
                            "expected": {"event_title": ground_truth.get("event_title"), "location": ground_truth.get("location"), "time": ground_truth.get("time")},
                            "found": {"event_title": event.event_title, "location": event.location, "time": event.time},
                            "timestamp": timestamp,
                            "description": f"Calendar event already satisfied before task execution"
                        })
                        
            # Check for multi-system task calendar_event component
            elif "calendar_event" in ground_truth:
                calendar_criteria = ground_truth["calendar_event"]
                for event in events:
                    matches = True
                    if "event_title_contains" in calendar_criteria and calendar_criteria["event_title_contains"].lower() not in event.event_title.lower():
                        matches = False
                    if "time" in calendar_criteria and event.time != calendar_criteria["time"]:
                        matches = False
                    if "location" in calendar_criteria and event.location != calendar_criteria["location"]:
                        matches = False
                    if matches:
                        self.precheck_failed = True
                        self.precheck_failure_details.append({
                            "system": "calendar",
                            "component": "calendar_event",
                            "expected": calendar_criteria,
                            "found": {"event_title": event.event_title, "location": event.location, "time": event.time},
                            "timestamp": timestamp,
                            "description": f"Calendar event already satisfied before task execution"
                        })
                        break
        except Exception as e:
            print(f"Warning: Calendar precheck failed: {e}")
    
    def _check_course_selection_precheck(self, ground_truth: dict, timestamp: float) -> None:
        """Check if course selection requirements are already satisfied"""
        try:
            draft_schedule = self.campus_environment.course_selection_system.get_draft_schedule_for_evaluation()
            
            # Check for course_selection task type ground truth
            if "expected_schedule_outcome" in ground_truth:
                expected_outcome = ground_truth["expected_schedule_outcome"]
                expected_sections = expected_outcome.get("selected_sections", [])
                
                if len(draft_schedule.selected_sections) > 0:
                    for expected in expected_sections:
                        for actual in draft_schedule.selected_sections:
                            if (actual.course_code == expected["course_code"] and
                                actual.assigned_pass == expected["assigned_pass"]):
                                self.precheck_failed = True
                                self.precheck_failure_details.append({
                                    "system": "course_selection",
                                    "component": "expected_schedule_outcome",
                                    "expected": expected,
                                    "found": {"course_code": actual.course_code, "assigned_pass": actual.assigned_pass},
                                    "timestamp": timestamp,
                                    "description": f"Course selection already satisfied before task execution"
                                })
                                
            # Check for multi-system task course_selected component
            elif "course_selected" in ground_truth:
                course_criteria = ground_truth["course_selected"]
                if "course_code" in course_criteria:
                    for section in draft_schedule.selected_sections:
                        if section.course_code == course_criteria["course_code"]:
                            if "assigned_pass" not in course_criteria or section.assigned_pass == course_criteria["assigned_pass"]:
                                self.precheck_failed = True
                                self.precheck_failure_details.append({
                                    "system": "course_selection",
                                    "component": "course_selected",
                                    "expected": course_criteria,
                                    "found": {"course_code": section.course_code, "assigned_pass": section.assigned_pass},
                                    "timestamp": timestamp,
                                    "description": f"Course selection already satisfied before task execution"
                                })
                                break
        except Exception as e:
            print(f"Warning: Course selection precheck failed: {e}")
    
    def _check_geography_precheck(self, ground_truth: dict, timestamp: float) -> None:
        """Check if geography/location requirements are already satisfied"""
        try:
            geo_state = self.campus_environment.geography_system.get_state_for_evaluation()
            
            # Check for walking_simple task type ground truth
            if "expected_outcome" in ground_truth:
                expected_outcome = ground_truth["expected_outcome"]
                target_location = expected_outcome.get("target_location_id")
                if target_location and hasattr(geo_state, 'current_location_id') and geo_state.current_location_id == target_location:
                    self.precheck_failed = True
                    self.precheck_failure_details.append({
                        "system": "geography",
                        "component": "expected_outcome.target_location_id",
                        "expected": target_location,
                        "found": geo_state.current_location_id,
                        "timestamp": timestamp,
                        "description": f"Target location already reached before task execution"
                    })
                    
            # Check for multi-system task location_reached component
            elif "location_reached" in ground_truth:
                location_criteria = ground_truth["location_reached"]
                if "current_location" in location_criteria:
                    current_location = getattr(geo_state, 'current_location_id', geo_state.get('current_location') if isinstance(geo_state, dict) else None)
                    if current_location == location_criteria["current_location"]:
                        self.precheck_failed = True
                        self.precheck_failure_details.append({
                            "system": "geography",
                            "component": "location_reached.current_location",
                            "expected": location_criteria["current_location"],
                            "found": current_location,
                            "timestamp": timestamp,
                            "description": f"Target location already reached before task execution"
                        })
        except Exception as e:
            print(f"Warning: Geography precheck failed: {e}")

    def _extract_system_type_from_action(self, action_content: str) -> str:
        """
        Extract system type from action content

        Args:
            action_content: The action content string

        Returns:
            System type identifier
        """
        # Map action patterns to system types
        if "email." in action_content.lower():
            return "email"
        elif "reservation." in action_content.lower():
            return "reservation"
        elif "calendar." in action_content.lower():
            return "calendar"
        elif "geography." in action_content.lower() or "walk_to" in action_content.lower():
            return "geography"
        elif "map." in action_content.lower():
            return "map"
        elif "course_selection." in action_content.lower():
            return "course_selection"
        elif "bibliography." in action_content.lower() or "data_system." in action_content.lower():
            return "information"
        else:
            return "unknown"

    def _validate_execution_sequence(self, ground_truth: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate that actions were executed in the correct sequence based on ground_truth order

        Args:
            ground_truth: Ground truth dictionary with expected components

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Extract expected sequence from ground_truth keys order
        expected_sequence = []
        system_mapping = {
            "email_sent": "email", "email": "email",
            "reservation_made": "reservation", "reservation": "reservation",
            "calendar_event": "calendar", "calendar": "calendar",
            "location_reached": "geography", "location": "geography",
            "course_selected": "course", "course": "course"
        }

        for key in ground_truth.keys():
            if key in system_mapping:
                system_type = system_mapping[key]
                if system_type not in expected_sequence:
                    expected_sequence.append(system_type)
            else:
                prefix = key.split('_')[0]
                if prefix in system_mapping:
                    system_type = system_mapping[prefix]
                    if system_type not in expected_sequence:
                        expected_sequence.append(system_type)

        if len(expected_sequence) <= 1:
            # No sequence validation needed for single or no components
            return True, "No sequence validation required"

        # Extract actual execution sequence from action history
        actual_sequence = []
        for action in self.action_history:
            if action["success"] and action["system_type"] in expected_sequence:
                # Only add if not already in sequence (avoid duplicates)
                if action["system_type"] not in actual_sequence:
                    actual_sequence.append(action["system_type"])

        # Validate sequence order
        for i, expected_system in enumerate(expected_sequence):
            if i >= len(actual_sequence):
                return False, f"Missing execution of {expected_system} system"

            if actual_sequence[i] != expected_system:
                return False, f"Wrong execution order: expected {expected_system} at position {i+1}, but got {actual_sequence[i]}"

        return True, f"Execution sequence is correct: {' → '.join(actual_sequence)}"
    
    def _enhance_evaluation_record(self, session: Session, task_item: CampusDatasetItem) -> None:
        """
        Enhance evaluation record with ground truth, task output, and location information
        This is a helper method that doesn't change existing evaluation logic
        
        Args:
            session: Current session
            task_item: Current task item
        """
        try:
            # Initialize detail_dict if it doesn't exist
            if session.evaluation_record.detail_dict is None:
                session.evaluation_record.detail_dict = {}
            
            # Add ground truth information
            session.evaluation_record.detail_dict["ground_truth"] = task_item.ground_truth
            
            # Add task output based on task type
            task_output = self._get_task_output_for_debug(task_item)
            if task_output is not None:
                session.evaluation_record.detail_dict["task_output"] = task_output
            
            # Add final location for require_place tasks
            if task_item.require_place:
                final_location = self.campus_environment.get_current_location_for_validation()
                session.evaluation_record.detail_dict["final_location"] = final_location
            
            # Add precheck information if this task required precheck
            if task_item.require_precheck:
                session.evaluation_record.detail_dict["precheck_required"] = True
                session.evaluation_record.detail_dict["precheck_failed"] = self.precheck_failed
                if self.precheck_failed:
                    session.evaluation_record.detail_dict["precheck_failure_details"] = self.precheck_failure_details
                    # Convert timestamps to readable format
                    import datetime
                    for detail in session.evaluation_record.detail_dict["precheck_failure_details"]:
                        detail["timestamp_readable"] = datetime.datetime.fromtimestamp(detail["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                
        except Exception as e:
            # Don't let enhancement errors affect the main evaluation
            print(f"Warning: Failed to enhance evaluation record: {e}")
    
    def _get_task_output_for_debug(self, task_item: CampusDatasetItem) -> Optional[Any]:
        """
        Get current task output for debugging purposes
        
        Args:
            task_item: Current task item
            
        Returns:
            Task output data or None if unable to retrieve
        """
        try:
            if task_item.task_type == "email_sending":
                latest_email = self.campus_environment.email_system.get_latest_email_for_evaluation()
                if latest_email:
                    return {
                        "recipient": getattr(latest_email, 'recipient', getattr(latest_email, 'to', None)),
                        "subject": getattr(latest_email, 'subject', None),
                        "body": getattr(latest_email, 'body', None)
                    }
                    
            elif task_item.task_type == "course_selection":
                draft_schedule = self.campus_environment.course_selection_system.get_draft_schedule_for_evaluation()
                if draft_schedule and hasattr(draft_schedule, 'selected_sections'):
                    return {
                        "selected_sections": [
                            {
                                "course_code": getattr(section, 'course_code', None),
                                "assigned_pass": getattr(section, 'assigned_pass', None),
                                "section_id": getattr(section, 'section_id', None)
                            }
                            for section in draft_schedule.selected_sections
                        ]
                    }
                    
            elif task_item.task_type == "walking_simple":
                geo_state = self.campus_environment.geography_system.get_state_for_evaluation()
                if geo_state:
                    return {
                        "current_location_id": getattr(geo_state, 'current_location_id', geo_state.get('current_location_id') if isinstance(geo_state, dict) else None),
                        "walk_history": getattr(geo_state, 'walk_history', geo_state.get('walk_history') if isinstance(geo_state, dict) else None)
                    }
                    
            elif task_item.task_type == "calendar_management":
                calendar_id = task_item.details.get("calendar_id", "self")
                events = self.campus_environment.calendar_system.get_calendar_events_for_evaluation(calendar_id)
                return {
                    "calendar_events": [
                        {
                            "event_title": getattr(event, 'event_title', None),
                            "location": getattr(event, 'location', None),
                            "time": getattr(event, 'time', None),
                            "description": getattr(event, 'description', None)
                        }
                        for event in events
                    ]
                }
                
            elif task_item.task_type == "reservation":
                reservations = self.campus_environment.reservation_system.get_reservations_for_evaluation(task_item.task_id)
                return {
                    "reservations": [
                        {
                            "seat_id": getattr(reservation, 'seat_id', reservation.get('seat_id') if isinstance(reservation, dict) else None),
                            "item_name": getattr(reservation, 'item_name', reservation.get('item_name') if isinstance(reservation, dict) else None),
                            "location_id": getattr(reservation, 'location_id', reservation.get('location_id') if isinstance(reservation, dict) else None),
                            "time_slot": getattr(reservation, 'time_slot', reservation.get('time_slot') if isinstance(reservation, dict) else None),
                            "date": getattr(reservation, 'date', reservation.get('date') if isinstance(reservation, dict) else None)
                        }
                        for reservation in reservations
                    ]
                }
                
            elif task_item.task_type == "quiz_question":
                # Get the last agent response for quiz questions
                if self._current_session and self._current_session.chat_history.get_value_length() > 0:
                    last_message = self._current_session.chat_history.get_item_deep_copy(-1)
                    parsed_result = self._parse_agent_response(last_message.content)
                    if parsed_result.action == AgentAction.FINISH and parsed_result.finish_reason == "quiz_answer":
                        return {
                            "agent_answer": parsed_result.content.replace("Answer: ", "").strip().upper()
                        }
                
            elif task_item.task_type == "multi_system":
                # For multi-system tasks, collect outputs from multiple systems
                multi_output = {}
                
                # Check each system component
                ground_truth = task_item.ground_truth
                if isinstance(ground_truth, dict):
                    if "email_sent" in ground_truth:
                        latest_email = self.campus_environment.email_system.get_latest_email_for_evaluation()
                        if latest_email:
                            multi_output["email"] = {
                                "recipient": getattr(latest_email, 'to', getattr(latest_email, 'recipient', None)),
                                "subject": getattr(latest_email, 'subject', None),
                                "body": getattr(latest_email, 'body', None)
                            }
                    
                    if "reservation_made" in ground_truth:
                        reservations = self.campus_environment.reservation_system.get_reservations_for_evaluation(task_item.task_id)
                        multi_output["reservations"] = [
                            {
                                "seat_id": getattr(r, 'seat_id', r.get('seat_id') if isinstance(r, dict) else None),
                                "item_name": getattr(r, 'item_name', r.get('item_name') if isinstance(r, dict) else None),
                                "location_id": getattr(r, 'location_id', r.get('location_id') if isinstance(r, dict) else None),
                                "time_slot": getattr(r, 'time_slot', r.get('time_slot') if isinstance(r, dict) else None),
                                "date": getattr(r, 'date', r.get('date') if isinstance(r, dict) else None)
                            }
                            for r in reservations
                        ]
                    
                    if "calendar_event" in ground_truth:
                        calendar_id = ground_truth["calendar_event"].get("calendar_id", "self")
                        events = self.campus_environment.calendar_system.get_calendar_events_for_evaluation(calendar_id)
                        multi_output["calendar_events"] = [
                            {
                                "event_title": getattr(event, 'event_title', None),
                                "location": getattr(event, 'location', None),
                                "time": getattr(event, 'time', None),
                                "description": getattr(event, 'description', None)
                            }
                            for event in events
                        ]
                    
                    if "location_reached" in ground_truth or "walk_to" in ground_truth:
                        geo_state = self.campus_environment.geography_system.get_state_for_evaluation()
                        if geo_state:
                            geo_output = {
                                "current_location_id": getattr(geo_state, 'current_location_id', geo_state.get('current_location_id') if isinstance(geo_state, dict) else None)
                            }
                            # For walk_to, also include walk_history for more detailed debugging
                            if "walk_to" in ground_truth:
                                geo_output["walk_history"] = getattr(geo_state, 'walk_history', geo_state.get('walk_history') if isinstance(geo_state, dict) else None)
                            multi_output["geography"] = geo_output
                    
                    if "course_selected" in ground_truth:
                        draft_schedule = self.campus_environment.course_selection_system.get_draft_schedule_for_evaluation()
                        if draft_schedule and hasattr(draft_schedule, 'selected_sections'):
                            multi_output["course_selection"] = {
                                "selected_sections": [
                                    {
                                        "course_code": getattr(section, 'course_code', None),
                                        "assigned_pass": getattr(section, 'assigned_pass', None)
                                    }
                                    for section in draft_schedule.selected_sections
                                ]
                            }
                
                return multi_output if multi_output else None
                
        except Exception as e:
            print(f"Warning: Failed to get task output for debug: {e}")
            return None
        
        return None

    def _check_affected_by_failed_prerequisite(self, task_id: str) -> Optional[str]:
        """
        Check if the given task_id is affected by any failed prerequisite task
        
        Args:
            task_id: The task ID to check
            
        Returns:
            The failed prerequisite task ID if affected, None otherwise
        """
        for failed_task_id, affected_task_ids in self.failed_prerequisite_tasks.items():
            if task_id in affected_task_ids:
                return failed_task_id
        return None

    def _record_failed_prerequisite_task(self, session: Session, current_item: CampusDatasetItem) -> None:
        """
        Record failed prerequisite task if current task failed and has pre_task_for field
        
        Args:
            session: Current session
            current_item: Current task item
        """
        # Check if current task failed
        if (session.evaluation_record.outcome == SessionEvaluationOutcome.INCORRECT and 
            current_item.pre_task_for is not None and 
            current_item.pre_task_for.strip() != ""):
            
            # Parse the comma-separated task IDs
            affected_task_ids = [task_id.strip() for task_id in current_item.pre_task_for.split(",") if task_id.strip()]
            
            if affected_task_ids:
                # Record this failed task and its affected tasks
                self.failed_prerequisite_tasks[current_item.task_id] = affected_task_ids
                print(f"📝 Task {current_item.task_id} failed - affecting {len(affected_task_ids)} downstream tasks: {', '.join(affected_task_ids)}")
                
                # Add this information to the current task's evaluation record
                if session.evaluation_record.detail_dict is None:
                    session.evaluation_record.detail_dict = {}
                session.evaluation_record.detail_dict["affects_downstream_tasks"] = affected_task_ids

    # ADDED: Method to save the complete state of the task and environment for checkpointing
    def save_checkpoint(self, session: Session) -> None:
        """
        Save the current state of the CampusTask and CampusEnvironment to disk.
        This allows for true stateful resume of experiments.
        """
        if not session.output_dir:
            print("Warning: output_dir not found in session, cannot save checkpoint.")
            return

        checkpoint_dir = Path(session.output_dir) / "checkpoint_state"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save the entire CampusEnvironment using pickle
        env_path = checkpoint_dir / "campus_environment.pkl"
        try:
            with open(env_path, 'wb') as f:
                pickle.dump(self.campus_environment, f)
        except Exception as e:
            print(f"Error saving CampusEnvironment checkpoint: {e}")

        # 2. Save the task-specific state using JSON
        task_state_path = checkpoint_dir / "campus_task_state.json"
        task_state = {
            "failed_prerequisite_tasks": self.failed_prerequisite_tasks,
            "_current_simulation_day": self._current_simulation_day,
        }
        try:
            with open(task_state_path, 'w', encoding='utf-8') as f:
                json.dump(task_state, f, indent=2)
        except Exception as e:
            print(f"Error saving CampusTask state checkpoint: {e}")

    # ADDED: Method to load the state from a checkpoint
    def _load_checkpoint(self, output_dir: str) -> None:
        """
        Load the task and environment state from a checkpoint if it exists.
        This is called once before the first task in a resumed session.
        """
        checkpoint_dir = Path(output_dir) / "checkpoint_state"
        if not checkpoint_dir.exists():
            return  # No checkpoint to load

        # 1. Load CampusEnvironment from pickle
        env_path = checkpoint_dir / "campus_environment.pkl"
        if env_path.exists():
            try:
                with open(env_path, 'rb') as f:
                    self.campus_environment = pickle.load(f)
                print("✅ Successfully loaded CampusEnvironment state from checkpoint.")
            except Exception as e:
                print(f"Warning: Failed to load CampusEnvironment checkpoint: {e}. Starting with a fresh environment.")

        # 2. Load CampusTask state from JSON
        task_state_path = checkpoint_dir / "campus_task_state.json"
        if task_state_path.exists():
            try:
                with open(task_state_path, 'r', encoding='utf-8') as f:
                    task_state = json.load(f)
                self.failed_prerequisite_tasks = task_state.get("failed_prerequisite_tasks", {})
                self._current_simulation_day = task_state.get("_current_simulation_day")
                print("✅ Successfully loaded CampusTask state from checkpoint.")
            except Exception as e:
                print(f"Warning: Failed to load CampusTask state checkpoint: {e}. Starting with fresh task state.")