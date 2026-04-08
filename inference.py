import asyncio
import os
import textwrap
from typing import List, Optional
import json

from openai import OpenAI

# Import our custom environment
from mock_network_env.models import NetworkAction
from mock_network_env.env import NetworkIncidentEnv

IMAGE_NAME = os.getenv("IMAGE_NAME") 
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
TASK_NAME = os.getenv("NETWORK_ENV_TASK", "easy")
BENCHMARK = os.getenv("NETWORK_ENV_BENCHMARK", "network-incident-response")
MAX_STEPS = 15
TEMPERATURE = 0.2 # Lower temperature for more deterministic bash commands
MAX_TOKENS = 150
SUCCESS_SCORE_THRESHOLD = 0.7  

# Max total reward is 1.0 (0.7 for the fix + 0.3 for the diagnostics)
MAX_TOTAL_REWARD = 1.0

# Update the System Prompt for a Network Engineer Persona
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an expert Network and Systems Engineer. You are logged into a broken Linux server via a terminal.
    Your job is to diagnose and fix the issue (e.g., Nginx, Firewall, or Routing). 
    
    CRITICAL RESTRICTIONS:
    This is a restricted diagnostic terminal. You are ONLY allowed to use the following commands:
    - cat (e.g., cat /var/log/syslog)
    - systemctl (e.g., systemctl status nginx or systemctl restart nginx)
    - ping (e.g., ping 10.0.1.5)
    - iptables (e.g., iptables -L or iptables -F)
    - ip (e.g., ip route, ip route del <subnet>, ip route add <subnet> via <gw>)
    - echo (for writing files. e.g., echo "server { listen 80; }" > /etc/nginx/nginx.conf)
    
    CRITICAL FIXING RULES:
    1. NGINX: Overwrite the bad config using a single-line echo command, then restart the service.
    2. FIREWALL: If a rogue rule is dropping traffic, flush the rules using exactly `iptables -F`.
    3. ROUTING: If a route has the wrong gateway, delete it using `ip route del <subnet>`, then add the correct one.
    4. VERIFICATION: ALWAYS verify your network fixes with a final `ping` to the target IP!
    5. Do NOT use whoami, ls, which, rm, or attempt to check/modify the $PATH.
    
    Reply with EXACTLY ONE bash command string per turn. No quotes, no markdown, no explanations.
    """
).strip()
# SYSTEM_PROMPT = textwrap.dedent(
#     """
#     You are an expert Network and Systems Engineer. You are logged into a broken Linux server via a terminal.
#     Your job is to diagnose and fix the issue (e.g., Nginx, Firewall, or Routing). 
    
#     CRITICAL RESTRICTIONS:
#     This is a restricted diagnostic terminal. You are ONLY allowed to use the following commands:
#     - cat (e.g., cat /var/log/syslog or cat /etc/nginx/nginx.conf)
#     - systemctl (e.g., systemctl status nginx or systemctl restart nginx)
#     - ping
#     - iptables
#     - ip route
#     - echo (for writing files. e.g., echo "server { listen 80; }" > /etc/nginx/nginx.conf)
    
#     CRITICAL FILE EDITING RULES:
#     1. If you find an error in a configuration file, OVERWRITE THAT EXACT FILE using a single-line echo command. 
#     2. Do NOT create new files in sites-available or sites-enabled. 
#     3. Do NOT use whoami, ls, which, rm, or attempt to check/modify the $PATH.
    
#     Reply with EXACTLY ONE bash command string per turn. No quotes, no markdown, no explanations.
#     """
# ).strip()
# SYSTEM_PROMPT = textwrap.dedent(
#     """
#     You are an expert Network and Systems Engineer. You are logged into a broken Linux server via a terminal.
#     Your job is to diagnose and fix the issue. You can use standard commands like 'cat', 'systemctl', 'ping', 'iptables', and 'ip route'.
#     To write or overwrite files, use the format: echo "content" > /path/to/file
    
#     CRITICAL INSTRUCTION: Reply with EXACTLY ONE bash command string per turn. No quotes, no markdown blocks, no prefixes. Just the raw command.
#     Example: cat /var/log/syslog
#     """
# ).strip()
# SYSTEM_PROMPT = textwrap.dedent(
#     """
#     You are an expert Network and Systems Engineer. You are logged into a broken Linux server via a terminal.
#     Your job is to diagnose and fix the issue (e.g., Nginx, Firewall, or Routing). 
    
#     CRITICAL RESTRICTIONS:
#     This is a restricted diagnostic terminal. You are ONLY allowed to use the following commands:
#     - cat (e.g., cat /var/log/syslog or cat /etc/nginx/nginx.conf)
#     - systemctl (e.g., systemctl status nginx or systemctl restart nginx)
#     - ping
#     - iptables
#     - ip route
#     - echo (for writing files, e.g., echo "content" > /path/to/file)
    
#     DO NOT use whoami, ls, which, rm, or attempt to check/modify the $PATH.
#     Reply with EXACTLY ONE bash command string per turn. No quotes, no markdown, no explanations.
#     """
# ).strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def build_user_prompt(step: int, last_stdout: str, last_stderr: str, last_reward: float, history: List[str]) -> str:
    history_block = "\n".join(history[-4:]) if history else "None"
    return textwrap.dedent(
        f"""
        Step: {step}
        Last Command Output (stdout): {last_stdout!r}
        Last Command Error (stderr): {last_stderr!r}
        Last reward: {last_reward:.2f}
        Previous steps:
        {history_block}
        
        Send your next bash command.
        """
    ).strip()

def get_model_message(client: OpenAI, step: int, last_stdout: str, last_stderr: str, last_reward: float, history: List[str]) -> str:
    user_prompt = build_user_prompt(step, last_stdout, last_stderr, last_reward, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        # Clean up markdown formatting if the LLM ignores instructions
        text = text.replace("```bash", "").replace("```", "").strip()
        return text if text else "echo 'No command generated'"
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "echo 'Model failure'"

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Initialize our custom environment
    env = await NetworkIncidentEnv.from_docker_image(IMAGE_NAME)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset() 
        last_stdout = result.observation.stdout
        last_stderr = result.observation.stderr
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if hasattr(result, 'done') and result.done:
                break

            command = get_model_message(client, step, last_stdout, last_stderr, last_reward, history)
            
            # Wrap the string in our Pydantic Action model
            action = NetworkAction(command=command, thought=None)
            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            error = None

            rewards.append(reward)
            steps_taken = step
            last_stdout = obs.stdout
            last_stderr = obs.stderr
            last_reward = reward

            log_step(step=step, action=command, reward=reward, done=done, error=error)
            history.append(f"Step {step}: {command!r} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
        score = min(max(score, 0.0), 1.0)  
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())