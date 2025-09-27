"""Agent abstractions for the WazAI Sentinel AI pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


class Agent(Protocol):
    """Protocol describing the minimum agent interface."""

    name: str

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent logic and return an updated payload."""


@dataclass
class AgentContext:
    """Execution context shared between agents."""

    config: Dict[str, Any]
    logger: Any
