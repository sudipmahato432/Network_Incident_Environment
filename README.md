# Network Incident Response Environment (OpenEnv)

## Description and Motivation
The **Network Incident Response Environment** is a deterministic, OpenEnv-compliant simulation designed to evaluate an LLM agent's ability to troubleshoot enterprise-level networking and server issues. 

In real-world DevOps and NOC (Network Operations Center) roles, engineers must navigate complex diagnostic paths. This environment moves beyond simple "pass/fail" metrics by implementing a **Dense Reward Function**, awarding partial credit for correct diagnostic behaviors (e.g., inspecting logs, checking service status) even if the final resolution is not reached.

## Action and Observation Spaces

### Action Space
The agent interacts with the environment using a Pydantic-validated `NetworkAction` model.
* **command**: A string representing a bash command (e.g., `systemctl status nginx`, `iptables -L`).
* **thought**: An optional field allowing the agent to perform Chain-of-Thought reasoning before execution.

### Observation Space
Returns a `NetworkObservation` model mirroring a POSIX terminal:
* **stdout/stderr**: Standard output and error streams.
* **exit_code**: Integer (0 for success, non-zero for failure).
* **pwd**: Current working directory.

## Task Descriptions & Difficulty
The environment provides three distinct failure scenarios:

1. **Easy: Nginx Port Misconfiguration**
   * **Issue**: Nginx is down due to an invalid port (800) in the config.
   * **Goal**: Fix the config and restart the service.
2. **Medium: Firewall Blockade**
   * **Issue**: A rogue iptables DROP rule is blocking database connectivity.
   * **Goal**: Identify the rule, flush the firewall, and verify via ping.
3. **Hard: Asymmetric Routing**
   * **Issue**: Incorrect gateway configuration for a specific subnet.
   * **Goal**: Update the routing table and verify destination reachability.

## Setup and Usage

### Prerequisites
* Python 3.10+
* Docker (for containerized validation)
* OpenAI-compatible API Key (Hugging Face or OpenAI)

### Installation
```bash
pip install -r requirements.txt