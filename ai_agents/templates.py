"""Reusable configuration templates for WazAI Sentinel."""
from __future__ import annotations

from typing import Any, Dict

from .diagnostics import DEFAULT_AGENT_ORDER


DEFAULT_CONFIG_TEMPLATE: Dict[str, Any] = {
    "log_level": "INFO",
    "action_threshold": "medium",
    "order": list(DEFAULT_AGENT_ORDER),
    "agents": {
        "investigator": {
            "provider": "openai",
            "model": "gpt-4o",
            "prompt": (
                "You are WazAI Sentinel's Investigator. Evaluate the alert data below and return "
                "JSON with keys summary, findings, risk. Use concise bullet lists. Data: {data}"
            ),
        },
        "triage": {
            "provider": "grok",
            "model": "grok-beta",
            "prompt": (
                "Determine severity (high/medium/low) and justification as JSON with keys "
                "severity and justification. Data: {data}"
            ),
        },
        "enricher": {
            "provider": "openai",
            "model": "gpt-4o",
            "prompt": (
                "Provide contextual threat intelligence, recommended response steps, and references. "
                "Return JSON with keys intel, actions, references. Data: {data}"
            ),
        },
        "correlator": {
            "provider": "openai",
            "model": "gpt-4o",
            "prompt": (
                "Correlate the alert with historical events, highlighting related incident IDs or tactics. "
                "Return JSON keys correlations and notes. Data: {data}"
            ),
        },
        "responder": {
            "provider": "openai",
            "model": "gpt-4o",
            "prompt": (
                "Provide an incident response action plan that aligns with organisational playbooks. "
                "Return JSON with keys actions (list of objects with type, reason, and parameters) "
                "and policy (string). Data: {data}"
            ),
        },
    },
    "actions": {
        "notify": {"channel": "security_ops"},
        "create_ticket": {"system": "jira"},
        "isolate_endpoint": {"enabled": False},
    },
}

