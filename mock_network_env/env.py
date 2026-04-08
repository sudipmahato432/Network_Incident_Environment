"""
The OpenEnv interface. This file bridges our mock server state machine 
with the strict step(), reset(), and state() async methods required by the spec.
"""

import os
from typing import Dict, Any
from pydantic import BaseModel

from .models import NetworkAction, NetworkObservation
from .state_machine import MockServerState

# --- OpenEnv Standard Return Types ---
class ResetResult(BaseModel):
    observation: NetworkObservation
    info: Dict[str, Any]

class StepResult(BaseModel):
    observation: NetworkObservation
    reward: float
    done: bool
    info: Dict[str, Any]

class NetworkIncidentEnv:
    def __init__(self):
        # We read the task level from the environment variable 
        # so the Judges can easily switch between easy/medium/hard
        self.task_level = os.getenv("NETWORK_ENV_TASK", "easy").lower()
        self.server = None
        self.step_count = 0
        
        # Grader memory to ensure we only award partial points once
        self._reward_state = {}

    @classmethod
    async def from_docker_image(cls, image_name: str = None):
        """Mocking the from_docker_image classmethod expected by the inference script."""
        return cls()

    async def reset(self) -> ResetResult:
        """
        Wipes the server state completely clean and resets the grader.
        This guarantees perfect compliance with the 'clean state' requirement.
        """
        self.server = MockServerState(self.task_level)
        self.step_count = 0
        
        self._reward_state = {
            "easy_status_checked": False,
            "easy_logs_read": False,
            "med_ping_failed": False,
            "med_firewall_checked": False,
            "hard_ping_failed": False,
            "hard_routes_checked": False
        }

        obs = NetworkObservation(
            stdout=f"Welcome to the Server Terminal. Task Level: {self.task_level.upper()}\nYou are root.",
            stderr="",
            exit_code=0,
            pwd=self.server.pwd
        )
        return ResetResult(observation=obs, info={"task": self.task_level})

    async def step(self, action: NetworkAction) -> StepResult:
        """
        Executes the agent's command and calculates the dense reward.
        """
        self.step_count += 1
        stdout, stderr, exit_code = self.server.execute(action.command)
        
        reward = 0.0
        done = False
        
        # ---------------------------------------------------------
        # THE GRADER: Calculating Dense Rewards (0.0 to 1.0 total)
        # ---------------------------------------------------------
        
        if self.task_level == "easy":
            if "checked_service" in self.server.diagnostics_run and not self._reward_state["easy_status_checked"]:
                reward += 0.1
                self._reward_state["easy_status_checked"] = True
                
            if "read_logs" in self.server.diagnostics_run and not self._reward_state["easy_logs_read"]:
                reward += 0.2
                self._reward_state["easy_logs_read"] = True
                
            if self.server.services.get("nginx") == "active":
                # The agent fixed the file and restarted the service successfully!
                reward += 0.7 
                done = True

        elif self.task_level == "medium":
            if "pinged" in self.server.diagnostics_run and not self._reward_state["med_ping_failed"]:
                reward += 0.1
                self._reward_state["med_ping_failed"] = True
                
            if "checked_firewall" in self.server.diagnostics_run and not self._reward_state["med_firewall_checked"]:
                reward += 0.2
                self._reward_state["med_firewall_checked"] = True
                
            # If firewall is cleared and agent runs a successful ping to verify
            if len(self.server.firewall_rules) == 0:
                if "ping" in action.command and "10.0.1.5" in action.command and exit_code == 0:
                    reward += 0.7
                    done = True

        elif self.task_level == "hard":
            if "pinged" in self.server.diagnostics_run and not self._reward_state["hard_ping_failed"]:
                reward += 0.1
                self._reward_state["hard_ping_failed"] = True
                
            if "checked_routes" in self.server.diagnostics_run and not self._reward_state["hard_routes_checked"]:
                reward += 0.2
                self._reward_state["hard_routes_checked"] = True
                
            # If the bad route is replaced with the correct gateway, and verified via ping
            if self.server.routes.get("10.0.2.0/24") == "10.0.0.1":
                if "ping" in action.command and "10.0.2." in action.command and exit_code == 0:
                    reward += 0.7
                    done = True

        # Failsafe: End the episode if the agent is stuck in an infinite loop
        if self.step_count >= 15:
            done = True

        # Package the observation
        obs = NetworkObservation(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            pwd=self.server.pwd
        )
        
        return StepResult(observation=obs, reward=reward, done=done, info={})

    async def state(self) -> Dict[str, Any]:
        """Returns the current state of the environment."""
        return {
            "task_level": self.task_level,
            "step_count": self.step_count,
            "nginx_status": self.server.services.get("nginx") if self.server else "unknown"
        }

    async def close(self):
        """Cleanup method. Required by the spec, even if we just pass."""
        pass