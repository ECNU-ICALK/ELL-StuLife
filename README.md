# ELL-StuLife
Building a Self-Evolving Agent via Experience-Driven Lifelong Learning: A Framework and Benchmark


![ELL](https://github.com/ECNU-ICALK/ELL-StuLife/blob/main/imgs/Framework.png?raw=true)

### What is ELL 🧐?

We introduce Experience-driven Lifelong Learning (ELL), a framework for building self-evolving agents capable of continuous growth through real-world interaction. Unlike traditional continual learning approaches, ELL emphasizes learning from experience: agents acquire knowledge not from static, labeled datasets, but through dynamic interaction with their environment. 
The framework is built on three core principles: 
- (1) **Experience Exploration**: Agents learn through continuous, self-motivated interaction with dynamic environments, navigating complex, long-horizon tasks and generating rich experiential trajectories. This ongoing engagement enables iterative self-correction and behavioral refinement, fostering learning that emerges from doing.
- (2) **Long-term Memory**: Agents preserve and structure historical knowledge, including personal experiences, domain expertise, and commonsense reasoning, into a persistent, accessible memory system. This supports long-range recall, contextual reasoning, and resistance to catastrophic forgetting, forming a stable foundation for lifelong growth.
- (3) **Skill Learning**: Agents abstract recurring patterns from experience into reusable skills, such as decision rules or functional modules. These skills are actively managed, refined, and validated through application in new tasks, enabling effective transfer, adaptation, and autonomous improvement.
Together, these enable agents to accumulate knowledge, adapt over time, and evolve autonomously.

![StuLife](https://github.com/ECNU-ICALK/ELL-StuLife/blob/main/imgs/stulife_fig1.png?raw=true)

### What is StuLife 🧐?

We also introduce `StuLife`, a benchmark dataset for ELL that simulates a student’s holistic college journey—from enrollment to academic and personal development—across three core phases and ten detailed sub-scenarios.

`StuLife` is designed around three key paradigm shifts:  
- **From Passive to Proactive**  
- **From Context to Memory**  
- **From Imitation to Learning**

It features a dynamic, interactive environment in which tasks are highly interconnected, and critical state variables—such as GPA, course availability, advisor relationships, and time—evolve based on the agent’s decisions. Agents must: 1) Autonomously acquire practical skills (e.g., course registration, scheduling, navigation, and communication), 2) Distill experiences into reusable knowledge, and 3) Maintain persistent memory to support future decision-making. Crucially, they are expected to exhibit intrinsic motivation by setting goals, anticipating future needs, and initiating actions without external prompting.

`StuLife` provides a comprehensive platform for evaluating lifelong learning capabilities, including memory retention, skill transfer, and autonomous, goal-directed behavior.

Beyond evaluating state-of-the-art LLMs on the `StuLife` benchmark, we also **explore the role of context engineering in advancing AGI**. Our results suggest that optimizing how we guide models may be as crucial as improving the models themselves, positioning context engineering as a key enabler of progress toward AGI.



# StuLife: A Persistent, Stateful Benchmark for Lifelong Language Agents

## Introduction

StuLife is a new benchmark built upon the `LifelongAgentBench` (LAB) framework, designed to evaluate the long-term memory, planning, adaptation, and autonomous decision-making capabilities of AI agents. It immerses agents in a persistent, stateful, and dynamic virtual university campus environment where their actions have lasting consequences.

Unlike traditional benchmarks that focus on stateless, single-turn tasks, StuLife creates a "virtual world" that evolves over a simulated academic year. An agent's success is not just about solving the immediate problem, but about managing their time, remembering commitments, and navigating a complex web of academic and social responsibilities that persist across hundreds of tasks.

## Core Concepts

StuLife is founded on three key principles to challenge the frontiers of agent intelligence:

*   **Persistent World**: The campus environment is a single, continuous Python object (`CampusEnvironment`). Every action an agent takes—from sending an email to reserving a study room—permanently alters the state of this world. A booked room remains booked for all subsequent tasks. This creates a single source of truth and forces the agent to deal with the long-term consequences of its decisions.

*   **Stateful & Dynamic Subsystems**: The world is composed of multiple interconnected subsystems (e.g., calendar, course selection, geography) that are dynamic and stateful. Course popularity fluctuates, room availability changes, and the agent's location persists between tasks. This requires the agent to constantly query the latest state of the world before acting, rather than relying on outdated information.

*   **Time-Driven & Self-Directed Tasks**: Agents are not always given explicit instructions. Instead, they operate on a simulated clock and must autonomously consult their internal calendar to understand "what to do next." Whether it's attending a class at 8:00 AM or a club meeting in the evening, the agent must demonstrate a sense of time and initiative, driven by the schedule it builds for itself.

## Architecture Overview

The benchmark's architecture is designed for simplicity and robustness, separating the world simulation from task execution.

*   **`CampusEnvironment`**: The "world simulator." A long-running Python class that instantiates and manages all subsystems (email, map, etc.). It maintains the global state and exposes a unified set of tools (APIs) for the agent to interact with the world. It contains no task-specific logic.

*   **`CampusTask`**: The "task controller." It loads task descriptions, presents them to the agent, and injects necessary context (like the current time and rules). It receives the agent's actions, executes them against the `CampusEnvironment`'s tools, and returns the results.

*   **`ToolManager` (Conceptual)**: A utility responsible for generating a `tools.json` file by reflecting on the methods exposed by `CampusEnvironment`. This provides the agent with a machine-readable, always-up-to-date manual of available tools and their usage.

## Simulated Subsystems

StuLife's virtual campus is powered by a rich set of interconnected subsystems, each designed to test different facets of an agent's reasoning and planning abilities:

*   **World Time & Calendar System**: Manages the flow of simulated time and allows the agent to manage personal, club, and academic schedules with different permission levels.
*   **Map & Geography System**: A deterministic system for navigating the campus. Agents must first find building IDs and plan optimal paths before they can physically move. Their location is persistent.
*   **Course Selection System**: A dynamic system where agents browse courses, manage a draft schedule, and use priority passes to register. Course popularity and seat availability change based on world events.
*   **Reservation System**: A global booking system for rooms and facilities. A successful reservation permanently alters the availability for all future tasks, testing the agent's ability to plan around resource contention.
*   **Email & Information System**: Allows agents to send formatted emails and query a rich, read-only database of campus information, from academic regulations in the Student Handbook to details about student clubs.

## How It Works: The Interaction Flow

An agent's life in StuLife follows a continuous `perceive -> think -> act` loop, driven by a series of time-based tasks.

1.  **Context Injection**: At the start of a task, the `CampusTask` provides the agent with the current simulated time and date (e.g., "Current time: Week 1, Monday 14:00").
2.  **Perception & Planning**: The agent perceives the time. An advanced agent might check its calendar to see what it's supposed to be doing. For example, it sees a "Study Session" scheduled at the library.
3.  **Action - Querying**: The agent checks its current location using `geography.get_current_location()`. It finds it's not at the library.
4.  **Action - Planning**: It uses `map.find_optimal_path` to get the walking route to the library.
5.  **Action - Execution**: It uses `geography.walk_to` with the calculated path to move to the library.
6.  **State Change & Verification**: The `CampusEnvironment` updates the agent's location. The task might require the agent to be at the library (`require_place` check) before it can be completed.
7.  **Task Completion**: Once all conditions are met, the agent calls the `finish()` action.

## Evaluation

Evaluation in StuLife goes beyond simple correctness. A task is marked as successful only if the agent achieves the desired final state while respecting all constraints. The `CampusTask` assesses performance by:

*   **State Validation**: Checking if the final state of the `CampusEnvironment` matches the task's ground truth. (e.g., Was the correct course added? Was the right email sent to the right person?).
*   **Constraint Satisfaction**: Verifying that all implicit and explicit task constraints were met (e.g., Was the meeting booked in the required building? Did the agent arrive on time?).
*   **Behavioral Sequence Validation**: For complex tasks, ensuring the agent followed a logical sequence of actions (e.g., checking availability *before* making a reservation).

## Dataset Overview

The benchmark includes a comprehensive dataset of **1284 tasks** spanning a full academic year. These tasks cover a wide range of scenarios, including:

*   Academic integrity and rule learning
*   Campus exploration and facility location
*   Course selection and schedule management
*   Attending 8 different multi-session courses
*   Interacting with academic advisors
*   Library resource usage and seat booking
*   Midterm and final exams
*   Joining and participating in student clubs

## 🚀 Getting Started & Running an Experiment

This section provides a comprehensive guide to setting up the environment and running a StuLife experiment. The following instructions assume you are in a bash shell environment.

### 1. Prerequisites

*   **Conda**: Ensure you have Miniconda or Anaconda installed to manage the environment.
*   **CUDA**: A compatible version of the CUDA Toolkit must be installed for GPU acceleration.

### 2. Environment Setup

First, clone the repository and prepare the Conda environment.

```bash
# Activate your conda environment
# (Replace 'stulife' with your environment name if different)
conda activate stulife

# Navigate to the project's root directory
# IMPORTANT: All subsequent commands must be run from this directory.
cd /path/to/your/framework/Stulife

echo "Current working directory: $(pwd)"
```

### 3. Configure Environment Variables

Before running the experiment, you need to configure several environment variables. You can save the following script as `setup_env.sh` in the project root and source it, or run the commands directly in your terminal.

```bash
#!/bin/bash

# --- Environment Variables Configuration ---
echo ">>> Configuring environment variables..."

# Set Hugging Face to offline mode to use local models
export HF_HOME=/path/to/your/model/cache # e.g., /data/model
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Add Conda and Python paths
export CPATH="${CONDA_PREFIX}/include:${CPATH}"
# Set PYTHONPATH to the project root for module resolution
export PYTHONPATH=.

# Setup CUDA runtime environment
# (Update CUDA_HOME to your CUDA installation path)
export CUDA_HOME=/path/to/your/cuda # e.g., /data/ljs/cuda-12.1
export PATH=${CUDA_HOME}/bin:${PATH}
export LD_LIBRARY_PATH=${CUDA_HOME}/lib:${LD_LIBRARY_PATH}

# Set PyTorch memory allocation policy
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo ">>> Environment variables configured."
```

To execute it:

```bash
source setup_env.sh
```

### 4. Run the Experiment

With the environment set up, you can now run an experiment using `run_experiment.py`. The script requires a path to a configuration file. All paths should be relative to the `Stulife` directory.

```bash
# --- Execute the Core Task ---
# Example using a local test configuration
# Note the relative path from the project root.
python ./src/run_experiment.py --config_path "../task_data/config/run_local_test.yaml"

```
