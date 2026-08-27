# GPT-5.5 vanilla

Paired baseline for `../GPT-5.5_Mubit-v2`. Category: Vanilla.

- Base model: `gpt-5.5` (OpenAI chat completions), `reasoning_effort: medium`,
  `max_completion_tokens: 16384`, default temperature, prompt budget
  262,144 tokens. Same settings as the memory arm.
- Harness: this repository at commit `7670764` with two non-behavioral
  additions from <https://github.com/mubit-ai/mubit-stulife-bench>: a
  `GenericOpenaiLanguageModel` wrapper (key from environment variable,
  explicit prompt-token budget) and a per-call usage log hook that writes
  `llm_usage.jsonl`. No memory callback. The calendar fix proposed in pull
  request #9 was not yet written when this arm ran; the agent never wrote
  to the calendar, so the fix does not affect its scores.
- Run: one pass over the full 1,284-sample stream (939 scored tasks),
  default sample order, 2026-08-21 14:57 to 23:58. `metric.json`:
  completed 99.84%, agent_context_limit 0.16%.

## Scores (official `calculate_stulife_metrics.py`)

| StuGPA | LTRR | PIS | In-Class success / turns | Daily Campus success / turns | Exam success / turns | Total success / turns |
|---|---|---|---|---|---|---|
| 17.92 | 12.09 | 0.00 | 0.00 / 4.01 | 38.20 / 9.76 | 16.88 / 2.54 | 20.98 / 6.68 |

StuGPA components: Exam 8.44 / 50 (27 of 160), Class 0 / 30 (0 of 334),
Advisor, Club, Personal responsibility together 9.49 / 20. HPS 9.45.

The StuGPA of 17.92 is close to the GPT-5 result reported in the StuLife
paper (17.9), which supports the setup as a faithful baseline.

Tokens (`llm_usage.jsonl`): 6,755 calls, 32.1M prompt tokens, 0.79M
completion tokens.

`stulife_metrics.json` is the unmodified output of
`calculate_stulife_metrics.py` for this directory. See
`../GPT-5.5_Mubit-v2/README.md` for the method and reproduction steps.
