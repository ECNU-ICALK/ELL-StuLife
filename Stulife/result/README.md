# Experiment Results

This directory contains the raw experiment trace for "Deepseek V3.1-Thinking" as an example.

For the traces of all other experiments, please visit [baidudisk](https://pan.baidu.com/s/1JQzDRgNrq_Qab5OihnguxA?pwd=fhd3).

## Submitted traces

| Directory | Category | Model | StuGPA |
|---|---|---|---|
| `GPT-5.5_Mubit-v2` | Memory | gpt-5.5 + Mubit memory callback (adapter v2) | 48.27 |
| `GPT-5.5_vanilla` | Vanilla | gpt-5.5, paired baseline for the entry above | 17.92 |

Each directory contains `runs.json`, `metric.json`, the resolved `config.yaml`, a per-call token log, the output of `calculate_stulife_metrics.py`, and a README with the method and reproduction steps.
