"""Utility helpers for running the AI pipeline from other components."""
from __future__ import annotations

from typing import Any, Dict

from . import SupervisorAgent, load_ai_config


def run_pipeline(alert: Dict[str, Any], config_path: str | None = None) -> Dict[str, Any]:
    """Execute the AI pipeline for *alert* and return an enriched copy."""
    config = load_ai_config(config_path)
    supervisor = SupervisorAgent(config)
    enriched = supervisor.run(alert)
    enriched["ai_actions"] = supervisor.decide_actions(enriched)
    return enriched
