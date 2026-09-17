# Topic

AgentSentinel is a lightweight research framework for studying indirect prompt injection attacks and runtime defenses in tool-using LLM agents. It focuses on how untrusted external content, such as files or emails, may influence an agent’s decision-making and trigger unsafe tool calls.

# AgentSentinel Code

This folder contains the code used in my AI Agent security exploration. Maybe they are too simple and even ugly. hahah

The project is still in an early stage, and this folder mainly records my learning and experiment process.

# Folder Description

- `agent/` : Agent related code
- `attacks/` : Attack experiments
- `benchmark/` : Evaluation scripts
- `defenses/` : Defense experiments
- `sandbox/` : Experiment environment
- `tests/` : Test files
- `results/` : Experiment results

# Run

The main demo can be started by "python run_demo.py" in bash.

# Project Value for Me

What matters most to me: This project helped me build a basic understanding of Agent security, and master the fundamental workflow of research exploration.

Then from the greater perspective, as LLM agents gain the ability to access data and perform real actions through external tools, prompt injection can lead to risks beyond incorrect text generation, including unauthorized operations and sensitive data leakage. This project provides a simple and reproducible environment for analyzing such attack chains and evaluating lightweight runtime security policies.
