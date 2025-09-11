# ELL-StuLife
Building a Self-Evolving Agent via Experience-Driven Lifelong Learning: A Framework and Benchmark


![ELL](https://github.com/ECNU-ICALK/ELL-StuLife/blob/main/imgs/Framework.png?raw=true)

### What is ELL 🧐?

We introduce Experience-driven Lifelong Learning (ELL), a framework for building self-evolving agents capable of continuous growth through real-world interaction. Unlike traditional continual learning approaches, ELL emphasizes learning from experience: agents acquire knowledge not from static, labeled datasets, but through dynamic interaction with their environment. 
The framework is built on four core principles: 
- (1) **Experience Exploration**: The agent must be capable of sequentially decomposing and executing complex, long-horizon tasks that involve **continuous interaction over minutes to hours with unquantifiable rewards**. Through sustained and **self-motivated** engagement, it generates rich experiential data, enabling iterative learning and self-correction. This persistent interaction allows the agent to progressively refine strategies and adapt behavior based on dynamic feedback, mimicking the trial-and-error process of real-world learning.

- (2) **Long-term Memory**: Experiential data is systematically processed and consolidated into persistent and structured memory, including raw observations, key events, learned facts, temporal contexts, and self-reflective insights. Memory is not passive storage but an active resource: it supports retrieval over long time spans, enables context-aware reasoning, and forms the foundation for future decision-making.

- (3) **Skill Learning**: The agent **abstracts recurring patterns from experience into reusable skills**, such as decision rules, functional modules, or problem-solving heuristics. These skills are explicitly constructed through reflection and validated through application in new and evolving tasks. The agent actively manages its skill repertoire, adding, refining, combining, or deprecating skills based on performance, creating a dynamic, self-improving system.

- (4) **Knowledge Internalization**: Beyond storing memories and reusing skills, the agent undergoes a process of **knowledge internalization**, transforming explicit and discrete knowledge into implicit and intuitive understanding. Over time, frequently used rules, patterns, and strategies are distilled into the agent's core reasoning process, reducing reliance on external retrieval or step-by-step reflection. This shift from deliberate application to automatic execution mirrors the cognitive transition from novice to expert, where learned behavior becomes "second nature".

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



# StuLife



StuLife is a new benchmark built upon the `LifelongAgentBench` (LAB) framework, designed to evaluate the long-term memory, planning, adaptation, and autonomous decision-making capabilities of AI agents. It immerses agents in a persistent, stateful, and dynamic virtual university campus environment where their actions have lasting consequences.

Unlike traditional benchmarks that focus on stateless, single-turn tasks, StuLife creates a "virtual world" that evolves over a simulated academic year. An agent's success is not just about solving the immediate problem, but about managing their time, remembering commitments, and navigating a complex web of academic and social responsibilities that persist across hundreds of tasks.

![StuLife2](https://github.com/ECNU-ICALK/ELL-StuLife/blob/main/imgs/stulife_fig2.png?raw=true)



StuLife is founded on three key principles to challenge the frontiers of agent intelligence:

*   **Persistent World**: The campus environment is a single, continuous Python object (`CampusEnvironment`). Every action an agent takes—from sending an email to reserving a study room—permanently alters the state of this world. A booked room remains booked for all subsequent tasks. This creates a single source of truth and forces the agent to deal with the long-term consequences of its decisions.

*   **Stateful & Dynamic Subsystems**: The world is composed of multiple interconnected subsystems (e.g., calendar, course selection, geography) that are dynamic and stateful. Course popularity fluctuates, room availability changes, and the agent's location persists between tasks. This requires the agent to constantly query the latest state of the world before acting, rather than relying on outdated information.

*   **Time-Driven & Self-Directed Tasks**: Agents are not always given explicit instructions. Instead, they operate on a simulated clock and must autonomously consult their internal calendar to understand "what to do next." Whether it's attending a class at 8:00 AM or a club meeting in the evening, the agent must demonstrate a sense of time and initiative, driven by the schedule it builds for itself.


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
