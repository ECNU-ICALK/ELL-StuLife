# GPT-5.5 + Mubit memory (adapter v2)

Submission for the StuLife leaderboard, category: Memory.

- Base model: `gpt-5.5` (OpenAI chat completions), `reasoning_effort: medium`,
  `max_completion_tokens: 16384`, default temperature (the API rejects
  `temperature: 0.0` for this model family), prompt budget 262,144 tokens.
- Memory system: [Mubit](https://mubit.ai), an agentic memory runtime,
  connected to the harness through one callback (`mubit_experience_callback`).
  A fresh, empty Mubit instance was used for this run.
- Harness: this repository at commit `7670764`, unmodified except for the
  items listed under "Changes to the harness" below.
- Run: one uninterrupted pass over the full 1,284-sample stream (939 scored
  tasks), default sample order, 2026-08-22 20:46 to 2026-08-23 05:14
  (8 h 28 min). No stop, no resume, no change to code or configuration
  during the run. `metric.json`: completed 99.36%, task_limit_reached 0.21%,
  agent_context_limit 0.43%, no environment or unknown errors.
- Paired baseline: `../GPT-5.5_vanilla` (same model, same settings, same
  task order, no memory callback).

## Scores (official `calculate_stulife_metrics.py`)

| StuGPA | LTRR | PIS | In-Class success / turns | Daily Campus success / turns | Exam success / turns | Total success / turns |
|---|---|---|---|---|---|---|
| 48.27 | 21.66 | 39.75 | 57.19 / 6.86 | 32.36 / 10.43 | 36.88 / 2.74 | 41.96 / 8.12 |

Baseline (`GPT-5.5_vanilla`): StuGPA 17.92, LTRR 12.09, PIS 0.00, In-Class
0.00 / 4.01, Daily Campus 38.20 / 9.76, Exam 16.88 / 2.54, Total 20.98 / 6.68.

StuGPA components for this run: Exam 18.44 / 50 (59 of 160 correct), Class
20.34 / 30 (191 fully correct, 71 correct location with wrong answer, 72 did
not arrive, of 334), Advisor 4.09 / 8 (23 of 45), Club 3.16 / 6 (50 of 95),
Personal responsibility 2.24 / 6 (28 of 75). HPS 42.77.

Paired against the baseline, 235 tasks flip from incorrect to correct and 38
flip from correct to incorrect. The lift concentrates where content from
earlier sessions is required: in-class quizzes (191 against 0), midterms (30
against 0), and finals (29 against 27).

Tokens (from `llm_usage.jsonl`, recorded per API call): 8,601 calls, 53.1M
prompt tokens, 1.19M completion tokens. Baseline: 6,755 calls, 32.1M prompt
tokens, 0.79M completion tokens.

`stulife_metrics.json` is the unmodified output of
`calculate_stulife_metrics.py` for this directory.

## Method

The agent, the prompts, the tools, and the task loop are the harness's own.
The callback adds a memory layer around each task session. Every read and
write is fail-open: if the memory server is unreachable, control flow does
not change.

**Recall** (`on_task_reset`). Before a session starts, the callback retrieves
from Mubit and appends the result to the first user message under a
reference-only framing line. The retrieval is typed, evidence-only, with no
server-side LLM call. The block has four parts, in this order:

1. Schedule digest (adapter v2). The latest banked `[stulife schedule]`
   digest for the registered course sections, with a rule to attend a class
   that meets now even if the world calendar is empty. Own character budget
   1,800. Recalled on every task.
2. Lessons distilled by Mubit's reflection step (`top_k_lessons: 6`).
3. Worked examples from earlier correct completions (`top_k_wins: 3`).
4. Lecture-note chunks (`top_k_notes: 6`, `note_query_chars: 1500`,
   `max_note_chunks_per_task: 14`), injected only on exam tasks. The query
   is the first 1,500 characters of the task text, so protocol names and
   other distinctive vocabulary drive retrieval.

Total injection cap `max_injection_chars: 20000`.

**Writes** (`on_task_complete`). After each session the callback stores: the
pass/fail step outcome; a win digest when the task was correct; an
observation digest for completed unscored (trigger) tasks; and every
substantial environment message the agent saw (lecture pages), as ~3,000
character chunks (`note_chunk_chars: 3000`, `min_note_part_chars: 1200`).
Writes do not depend on the outcome.

**Schedule memory** (adapter v2). The callback parses meeting times and
locations that the agent itself observed, from catalog browse results,
timetables quoted in task instructions, and registration confirmations,
into a per-section catalog (`callback_state/callback_2/mubit_experience_state.json`).
When the registered set or its details change, it banks a compact digest.
This makes attendance depend on stored observations rather than on whether
the model happened to copy its schedule into the campus calendar at
enrollment, which at default temperature it does in roughly 7 of 10 runs.

**Reflection.** Every 6 completed tasks (`reflect_every: 6`) Mubit distills
lessons from the recorded outcomes. Later sessions receive these lessons
through the recall path.

Only what the agent experienced is written: task text, its own trajectory,
the environment messages it received, and the pass/fail bit. No gold
answers and no evaluation internals are stored or injected.

## Changes to the harness

All changes are in the public adapter repository
<https://github.com/mubit-ai/mubit-stulife-bench> (commit `3742459`), as
`patches/upstream.patch` plus `overlay/`. Applied on top of upstream commit
`7670764`:

1. Calendar date matching fix (`systems/world_and_calendar.py`,
   `_is_date_match`). Upstream accepts calendar events whose time strings it
   then never matches: plural `"Weeks 1-18"` and day lists such as
   `"Monday/Wednesday/Friday"`. The fix parses both forms and keeps the
   strict negatives. It is proposed upstream as pull request #9. This run
   had the fix active from task 1. The vanilla baseline ran before the fix
   was written; that agent never wrote to the calendar, so the fix does not
   affect its scores.
2. Callback registration (`callbacks/constructor.py`,
   `callbacks/instance/__init__.py`, `configs/definition.yaml`) for
   `mubit_experience_callback`.
3. `GenericOpenaiLanguageModel` (`language_models/instance/`), an
   `OpenaiLanguageModel` subclass that reads the key from an environment
   variable and sets an explicit prompt-token budget. Models absent from
   the upstream context-length table are otherwise truncated to 4,096
   prompt tokens.
4. A per-call usage log hook in `openai_language_model.py` that writes
   `llm_usage.jsonl`. It does not change requests or responses.

Both arms in this submission use changes 3 and 4. Only the memory arm uses
change 2. Change 1 is in the memory arm only, for the reason given above.

## Reproduce

```bash
git clone https://github.com/mubit-ai/mubit-stulife-bench && cd mubit-stulife-bench
./setup.sh                                   # clones upstream @ 7670764, applies patch + overlay
export OPENAI_API_KEY=...
export MUBIT_ENDPOINT=...  MUBIT_API_KEY=... # fresh Mubit instance
cd ELL-StuLife/Stulife
python src/run_experiment.py --config_path configs/assignments/mubit/full_prem_mubit_v2.yaml
python src/run_experiment.py --config_path configs/assignments/mubit/full_prem_cold.yaml
```

The resolved configuration of each run is in `config.yaml` in its directory.

## Known limitations

- One run per arm. gpt-5.5 runs at the API default temperature, so the
  arms are not deterministic. No variance estimate is reported.
- Cold gpt-5.5 scores 0 on in-class and midterm tasks. Those tasks are only
  delivered when the agent reads its schedule and attends; the cold agent
  does not do this on its own. The memory arm learned the convention from
  its own reflected lessons during the stream.
- The `course_selection_eval/`, `self_schedule/`, `current_session.json`,
  and `exception.txt` files are the harness's own outputs, included as
  produced. `checkpoint_state/` (a pickled environment) is omitted for size.
