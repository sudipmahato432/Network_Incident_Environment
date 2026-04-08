"""
Pydantic models defining the Action and Observation spaces for the Network Incident Environment.
Strict typing here ensures the LLM understands exactly what to output and what to expect.
"""

from typing import Optional
from pydantic import BaseModel, Field

class NetworkAction(BaseModel):
    """
    The action space for the agent. Represents a single terminal execution.
    """
    thought: Optional[str] = Field(
        default=None,
        description="Optional scratchpad for your internal reasoning. Use this to explain WHY you are running the command before you execute it."
    )
    command: str = Field(
        ..., # The ellipsis means this field is strictly required
        description=(
            "The exact bash command to execute in the terminal. "
            "Examples: 'systemctl status nginx', 'cat /etc/nginx/nginx.conf', "
            "'ping -c 4 10.0.1.5', 'iptables -L -n -v', 'ip route'."
        )
    )

class NetworkObservation(BaseModel):
    """
    The observation space returned to the agent after an action.
    Mirrors standard POSIX terminal output.
    """
    stdout: str = Field(
        ..., 
        description="The standard output stream resulting from the command."
    )
    stderr: str = Field(
        ..., 
        description="The standard error stream. If this is not empty, the command likely failed."
    )
    exit_code: int = Field(
        ..., 
        description="The integer exit code of the command. 0 indicates success, anything else indicates an error."
    )
    pwd: str = Field(
        ..., 
        description="The present working directory of the terminal."
    )