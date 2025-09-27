"""Utility helpers for running the AI pipeline from other components."""
from __future__ import annotations

from typing import Any, Dict

from .config import load_ai_config
from .supervisor import SupervisorAgent


def run_pipeline(
    alert: Dict[str, Any],
    config_path: str | None = None,
    *,
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Execute the AI pipeline for *alert* and return an enriched copy."""
    config = config if config is not None else load_ai_config(config_path)
    supervisor = SupervisorAgent(config)
    enriched = supervisor.run(alert)
    actions = supervisor.decide_actions(enriched)
    enriched["ai_actions"] = actions
    enriched["ai_action_results"] = supervisor.execute_actions(actions)
    return enriched
