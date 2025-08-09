# ELL-StuLife
Building a Self-Evolving Agent via Experience-Driven Lifelong Learning: A Framework and Benchmark


![ELL](https://raw.githubusercontent.com/matteobettini/benchmarl_sphinx_theme/master/benchmarl_sphinx_theme/static/img/benchmarl.png?raw=true)

### What is ELL 🧐?

We introduce Experience-driven Lifelong Learning (ELL), a framework for building self-evolving agents capable of continuous growth through real-world interaction. Unlike traditional continual learning approaches, ELL emphasizes learning from experience: agents acquire knowledge not from static, labeled datasets, but through dynamic interaction with their environment. 
The framework is built on three core principles: 
- (1) **Experience Exploration**: Agents learn through continuous, self-motivated interaction with dynamic environments, navigating complex, long-horizon tasks and generating rich experiential trajectories. This ongoing engagement enables iterative self-correction and behavioral refinement, fostering learning that emerges from doing.
- (2) **Long-term Memory**: Agents preserve and structure historical knowledge, including personal experiences, domain expertise, and commonsense reasoning, into a persistent, accessible memory system. This supports long-range recall, contextual reasoning, and resistance to catastrophic forgetting, forming a stable foundation for lifelong growth.
- (3) **Skill Learning**: Agents abstract recurring patterns from experience into reusable skills, such as decision rules or functional modules. These skills are actively managed, refined, and validated through application in new tasks, enabling effective transfer, adaptation, and autonomous improvement.
Together, these enable agents to accumulate knowledge, adapt over time, and evolve autonomously.

### What is StuLife 🧐?

We also introduce `StuLife`, a benchmark dataset for ELL that simulates a student’s holistic college journey—from enrollment to academic and personal development—across three core phases and ten detailed sub-scenarios.

`StuLife` is designed around three key paradigm shifts:  
- **From Passive to Proactive**  
- **From Context to Memory**  
- **From Imitation to Learning**

It features a dynamic, interactive environment in which tasks are highly interconnected, and critical state variables—such as GPA, course availability, advisor relationships, and time—evolve based on the agent’s decisions. Agents must:

- Autonomously acquire practical skills (e.g., course registration, scheduling, navigation, and communication),  
- Distill experiences into reusable knowledge,  
- Maintain persistent memory to support future decision-making.

Crucially, they are expected to exhibit intrinsic motivation by setting goals, anticipating future needs, and initiating actions without external prompting.

`StuLife` provides a comprehensive platform for evaluating lifelong learning capabilities, including memory retention, skill transfer, and autonomous, goal-directed behavior.

Beyond evaluating state-of-the-art LLMs on the `StuLife` benchmark, we also **explore the role of context engineering in advancing AGI**. Our results suggest that optimizing how we guide models may be as crucial as improving the models themselves, positioning context engineering as a key enabler of progress toward AGI.