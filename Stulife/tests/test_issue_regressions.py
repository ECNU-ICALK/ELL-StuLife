from __future__ import annotations

import collections
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_PATH = REPO_ROOT / "task_data" / "tasks.json"
COURSES_PATH = REPO_ROOT / "task_data" / "background" / "courses.json"
LIB_MAP_PATH = REPO_ROOT / "task_data" / "background" / "info" / "lib_map_with_seats.json"

COURSE_DELTA_INTROS = [
    "To make the target draft update explicit, carry out exactly these changes: ",
    "Please treat the following as the authoritative draft update and apply each step exactly: ",
    "For clarity, the draft schedule should be updated in exactly this way: ",
    "To avoid any ambiguity, make the following draft-schedule edits exactly as written: ",
    "Use this exact set of draft changes, even if the earlier narrative sounds less specific: ",
    "The concrete draft adjustments you should execute are the following: ",
    "Please use the exact draft edits below as the final instruction set: ",
    "To pin down the intended outcome, apply these draft-schedule changes exactly: ",
    "The required draft delta is listed here; execute each change exactly: ",
    "If any earlier wording feels fuzzy, follow these precise draft updates instead: ",
    "Treat the next line as the definitive draft revision and apply it exactly: ",
    "Here is the exact draft-schedule delta you should perform: ",
    "To state the intended schedule outcome plainly, make these exact edits: ",
    "Please follow this precise draft-change checklist rather than relying on the broader wording above: ",
    "The unambiguous draft actions are listed below; execute them exactly: ",
    "For a precise interpretation of this task, update the draft exactly as follows: ",
    "Use the exact schedule-edit instructions below to complete this task: ",
    "The draft should end up changing in this exact way: ",
    "To make the section and pass targets explicit, apply these exact edits: ",
    "Please resolve any ambiguity by following these exact draft-schedule operations: ",
    "The intended draft modifications are precisely these: ",
    "To remove guesswork, execute the following draft updates exactly as stated: ",
    "The exact draft-schedule operations for this task are the following: ",
    "Please rely on this precise draft delta as the binding instruction: ",
]

SEND_PAT = re.compile(r"send (?:an |another |a follow-up )?email to\s+", re.I)
SUBJECT_PAT = re.compile(r"\s+with the subject\s+", re.I)
BODY_PAT = re.compile(r"\s+and body\s+", re.I)
BOUNDARY_MARKERS = [
    ". Once that's done",
    ". Once that’s done",
    ". Once the booking is confirmed",
    ". Once the room is booked",
    ". Once the time is set and the room is booked",
    ". After that is confirmed",
    ". After the email is sent",
    ". Finally,",
    ". Next,",
    ". Then,",
    ". Remember,",
    ". I appreciate you handling these arrangements.",
    ". I appreciate you handling these arrangements promptly.",
    ". Oh, by the way,",
    ". Please ensure",
    ". Thanks!",
    ". You can complete these bookings",
    ". This email will",
    ". This will ",
]
SIGNATURE_TRAIL_RE = re.compile(r"(Research Assistant to Professor [A-Za-z .]+?)(?:,| to ).*$", re.M)


def load_tasks() -> dict:
    return json.loads(TASKS_PATH.read_text(encoding="utf-8"))


def load_courses() -> dict[str, dict]:
    courses = json.loads(COURSES_PATH.read_text(encoding="utf-8"))["courses"]
    return {course["course_code"]: course for course in courses}


def base_code(code: str) -> str:
    return code.split("(")[0]


def course_label(course_by_code: dict[str, dict], code: str) -> str:
    course = course_by_code[code]
    return f"'{course['course_name']}' section {code} taught by {course['instructor']['name']}"


def strip_explicit_suffix(instruction: str) -> str:
    marker_indices = [instruction.find(marker) for marker in COURSE_DELTA_INTROS if instruction.find(marker) != -1]
    if not marker_indices:
        return instruction.rstrip()
    marker_index = min(marker_indices)
    return instruction[:marker_index].rstrip()


def iter_course_selection_tasks(tasks: dict, pattern: str) -> list[tuple[str, dict]]:
    regex = re.compile(pattern)
    items = []
    for key, task in tasks.items():
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id", "")
        match = regex.fullmatch(task_id)
        if match:
            items.append((int(match.group(1)), key, task))
    return [item[1:] for item in sorted(items)]


def expected_delta_actions(course_by_code: dict[str, dict], previous_task: dict, current_task: dict) -> str | None:
    previous_sections = previous_task["ground_truth"]["expected_schedule_outcome"]["selected_sections"]
    current_sections = current_task["ground_truth"]["expected_schedule_outcome"]["selected_sections"]

    previous_by_base = {base_code(section["course_code"]): section for section in previous_sections}
    current_by_base = {base_code(section["course_code"]): section for section in current_sections}

    has_structural_delta = False
    actions = []

    for previous_section in previous_sections:
        previous_base = base_code(previous_section["course_code"])
        if previous_base not in current_by_base:
            has_structural_delta = True
            actions.append(
                f"remove {course_label(course_by_code, previous_section['course_code'])} from your draft schedule"
            )

    for current_section in current_sections:
        current_base = base_code(current_section["course_code"])
        if current_base not in previous_by_base:
            has_structural_delta = True
            actions.append(
                f"add {course_label(course_by_code, current_section['course_code'])} to your draft schedule with pass {current_section['assigned_pass']}"
            )

    for current_section in current_sections:
        current_base = base_code(current_section["course_code"])
        if current_base not in previous_by_base:
            continue
        previous_section = previous_by_base[current_base]
        if previous_section["course_code"] != current_section["course_code"]:
            has_structural_delta = True
            actions.append(
                f"switch '{course_by_code[current_section['course_code']]['course_name']}' from section {previous_section['course_code']} taught by {course_by_code[previous_section['course_code']]['instructor']['name']} "
                f"to section {current_section['course_code']} taught by {course_by_code[current_section['course_code']]['instructor']['name']}, and set its pass to {current_section['assigned_pass']}"
            )
        elif previous_section["assigned_pass"] != current_section["assigned_pass"]:
            actions.append(
                f"change {course_label(course_by_code, current_section['course_code'])} from {previous_section['assigned_pass']} to {current_section['assigned_pass']}"
            )

    if not has_structural_delta:
        return None

    return "; ".join(actions) + "."


def find_delta_intro(instruction: str) -> str | None:
    indices = [(instruction.find(marker), marker) for marker in COURSE_DELTA_INTROS if instruction.find(marker) != -1]
    if not indices:
        return None
    _, marker = min(indices, key=lambda item: item[0])
    return marker


def strip_wrappers(value: str) -> str:
    value = value.strip()
    changed = True
    while changed:
        changed = False
        for start, end in [('`"', '"`'), ("`'", "'`"), ("`", "`"), ('"', '"'), ("'", "'")]:
            if value.startswith(start) and value.endswith(end) and len(value) >= len(start) + len(end):
                value = value[len(start) : -len(end)].strip()
                changed = True
    return value


def normalize_email_body(value: str) -> str:
    return SIGNATURE_TRAIL_RE.sub(r"\1", value.strip()).strip()


def read_wrapped(text: str, position: int) -> tuple[str | None, int]:
    for start, end in [('`"', '"`'), ("`'", "'`"), ("`", "`"), ('"', '"'), ("'", "'")]:
        if text.startswith(start, position):
            end_index = text.find(end, position + len(start))
            if end_index != -1:
                return text[position + len(start) : end_index], end_index + len(end)
    return None, position


def find_boundary(text: str, position: int) -> int:
    indices = [text.find(marker, position) for marker in BOUNDARY_MARKERS if text.find(marker, position) != -1]
    return min(indices) if indices else len(text)


def parse_trigger_emails(task: dict) -> list[dict[str, str]]:
    instruction = task.get("instruction", "")
    parsed = []
    cursor = 0
    while True:
        send_match = SEND_PAT.search(instruction, cursor)
        if not send_match:
            break
        cursor = send_match.end()

        recipient, new_cursor = read_wrapped(instruction, cursor)
        if recipient is None:
            recipient_match = re.match(r"([^\s]+)", instruction[cursor:])
            assert recipient_match is not None, task["task_id"]
            recipient = recipient_match.group(1)
            cursor += len(recipient)
        else:
            cursor = new_cursor

        subject_match = SUBJECT_PAT.search(instruction, cursor)
        assert subject_match is not None, task["task_id"]
        cursor = subject_match.end()

        subject, new_cursor = read_wrapped(instruction, cursor)
        if subject is None:
            body_anchor = BODY_PAT.search(instruction, cursor)
            assert body_anchor is not None, task["task_id"]
            subject = instruction[cursor:body_anchor.start()]
            cursor = body_anchor.start()
        else:
            cursor = new_cursor

        body_match = BODY_PAT.search(instruction, cursor)
        assert body_match is not None, task["task_id"]
        cursor = body_match.end()

        body, new_cursor = read_wrapped(instruction, cursor)
        if body is None:
            boundary = find_boundary(instruction, cursor)
            body = instruction[cursor:boundary]
            cursor = boundary
        else:
            cursor = new_cursor

        parsed.append(
            {
                "recipient": strip_wrappers(recipient),
                "subject_contains": strip_wrappers(subject),
                "body_contains": normalize_email_body(strip_wrappers(body)),
            }
        )

    arrival_match = re.search(r"body and subject are both ['\"]([^'\"]+)['\"]", instruction)
    if arrival_match:
        advisor_email = None
        for change in task.get("world_state_change", []):
            if change.get("action") == "set_advisor_availability":
                advisor_email = change.get("parameters", {}).get("advisor_id")
                if advisor_email:
                    break
        assert advisor_email, task["task_id"]
        arrival_text = arrival_match.group(1)
        parsed.append(
            {
                "recipient": advisor_email,
                "subject_contains": arrival_text,
                "body_contains": arrival_text,
            }
        )

    return parsed


def align_email_fields(email_fields: dict[str, dict], parsed_emails: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    aligned = {}
    used_indices = set()
    grouped_by_recipient = collections.defaultdict(list)
    for index, email in enumerate(parsed_emails):
        grouped_by_recipient[email["recipient"]].append((index, email))

    recipient_counters = collections.Counter()
    for field, value in email_fields.items():
        recipient = value.get("recipient")
        matches = grouped_by_recipient.get(recipient, [])
        if matches:
            match_index = recipient_counters[recipient]
            if match_index < len(matches):
                parsed_index, parsed_email = matches[match_index]
                aligned[field] = parsed_email
                used_indices.add(parsed_index)
                recipient_counters[recipient] += 1

    for field, value in email_fields.items():
        if field in aligned:
            continue
        subject = value.get("subject_contains")
        remaining_matches = [
            (index, email)
            for index, email in enumerate(parsed_emails)
            if index not in used_indices and email["subject_contains"] == subject
        ]
        if len(remaining_matches) == 1:
            parsed_index, parsed_email = remaining_matches[0]
            aligned[field] = parsed_email
            used_indices.add(parsed_index)

    remaining = [(index, email) for index, email in enumerate(parsed_emails) if index not in used_indices]
    for field in email_fields:
        if field in aligned:
            continue
        assert remaining, field
        parsed_index, parsed_email = remaining.pop(0)
        aligned[field] = parsed_email
        used_indices.add(parsed_index)

    return aligned


def test_course_selection_structural_deltas_have_exact_actions_and_bounded_template_reuse():
    tasks = load_tasks()
    course_by_code = load_courses()
    intro_usage = collections.Counter()

    for sequence in (
        iter_course_selection_tasks(tasks, r"course_selection_(\d{3})"),
        iter_course_selection_tasks(tasks, r"course_selection_s2_(\d{3})"),
    ):
        if not sequence:
            continue
        assert find_delta_intro(sequence[0][1]["instruction"]) is None
        for index in range(1, len(sequence)):
            _, previous_task = sequence[index - 1]
            _, current_task = sequence[index]
            expected_actions = expected_delta_actions(course_by_code, previous_task, current_task)
            instruction = current_task["instruction"]
            intro = find_delta_intro(instruction)
            if expected_actions is None:
                assert intro is None
            else:
                assert intro in COURSE_DELTA_INTROS, current_task["task_id"]
                assert instruction.endswith(intro + expected_actions), current_task["task_id"]
                intro_usage[intro] += 1

    assert intro_usage
    assert max(intro_usage.values()) <= 3


def test_paired_email_ground_truth_matches_trigger_instruction():
    tasks = load_tasks()
    trigger_map = {
        task["task_id"]: task
        for task in tasks.values()
        if isinstance(task, dict) and "task_id" in task
    }

    for task in tasks.values():
        if not isinstance(task, dict):
            continue
        ground_truth = task.get("ground_truth")
        if not isinstance(ground_truth, dict):
            continue

        email_fields = {
            field: value
            for field, value in ground_truth.items()
            if (field.startswith("email_") or field.startswith("email_sent")) and isinstance(value, dict)
        }
        trigger_task = trigger_map.get(f"{task['task_id']}_trigger")
        if not email_fields or trigger_task is None:
            continue

        aligned_fields = align_email_fields(email_fields, parse_trigger_emails(trigger_task))
        for field, expected_email in aligned_fields.items():
            assert ground_truth[field]["recipient"] == expected_email["recipient"], (task["task_id"], field)
            assert ground_truth[field]["subject_contains"] == expected_email["subject_contains"], (task["task_id"], field)
            assert ground_truth[field]["body_contains"] == expected_email["body_contains"], (task["task_id"], field)


def test_issue_6_specific_ground_truth_fixes():
    tasks = load_tasks()

    club_066 = tasks["293_club_task_066"]["ground_truth"]["calendar_event"]
    assert club_066["calendar_id"] == "club_c062"

    club_089 = tasks["359_club_task_089"]["ground_truth"]["reservation_made_2"]
    assert club_089["location_id"] == "B105"


def test_issue_7_library_room_names_match_seat_ids():
    tasks = load_tasks()
    libraries = json.loads(LIB_MAP_PATH.read_text(encoding="utf-8"))["libraries"]

    seat_to_room = {}
    for library in libraries:
        for rooms in library.get("internal_amenities", {}).values():
            for room in rooms:
                for seat in room.get("seats", []):
                    seat_to_room[seat["seat_id"]] = room["room_name"]

    for key in [
        "659_libstudy_task_027",
        "713_libstudy_task_054",
        "842_libstudy_task_037",
        "849_libstudy_task_010",
        "898_libstudy_task_038",
        "1003_libstudy_task_032",
    ]:
        reservation = tasks[key]["ground_truth"]["reservation_made"]
        assert reservation["item_name"] == seat_to_room[reservation["seat_id"]], key
