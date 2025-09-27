"""Diagnostics helpers for WazAI Sentinel configuration and runtime checks."""
from __future__ import annotations

import copy
import os
from importlib import util as importlib_util
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


DEFAULT_AGENT_ORDER: Tuple[str, ...] = (
    "investigator",
    "triage",
    "enricher",
    "correlator",
    "responder",
)

PROVIDER_ENV_VARS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "grok": "GROK_API_KEY",
}

PROVIDER_DEPENDENCIES: Dict[str, Tuple[str, ...]] = {
    "openai": ("requests",),
    "grok": ("requests",),
}

OFFLINE_AGENT_RESPONSES: Dict[str, Dict[str, Any]] = {
    "investigator": {
        "summary": "Offline analysis placeholder",
        "findings": ["No live API calls were made."],
        "risk": "medium",
    },
    "triage": {
        "severity": "medium",
        "justification": "Offline mode assumes moderate impact for demonstration.",
    },
    "enricher": {
        "intel": ["Add live threat intelligence by disabling offline mode."],
        "actions": ["Review host hardening", "Collect additional telemetry"],
        "references": ["https://wazai.example/offline"],
    },
    "correlator": {
        "correlations": ["Historical event correlation not available offline"],
        "notes": "Connect to production data sources for full correlation.",
    },
    "responder": {
        "actions": [
            {
                "type": "notify",
                "channel": "security_ops",
                "reason": "Offline demo generated notification",
            }
        ],
        "policy": "Escalate through standard SOC workflow during offline demos.",
    },
}


def _normalise_agents(config: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    agents_cfg = config.get("agents")
    if not isinstance(agents_cfg, Mapping):
        return {}
    normalised: Dict[str, Dict[str, Any]] = {}
    for name, value in agents_cfg.items():
        if isinstance(name, str) and isinstance(value, Mapping):
            normalised[name] = dict(value)
    return normalised


def validate_config(config: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    """Validate *config* returning a tuple of ``(errors, warnings)``."""

    errors: List[str] = []
    warnings: List[str] = []

    if not config:
        warnings.append(
            "Configuration file not found or empty; defaults will be used when running the pipeline."
        )
        return errors, warnings

    agents = _normalise_agents(config)
    if not agents:
        errors.append("No agents are defined under the 'agents' section.")

    order = config.get("order")
    if order is None:
        warnings.append("Pipeline order not specified; using default agent order.")
        order_seq: Sequence[str] = DEFAULT_AGENT_ORDER
    elif isinstance(order, Sequence) and not isinstance(order, (str, bytes)):
        order_seq = [str(name) for name in order]
    else:
        errors.append("The 'order' setting must be a list of agent names.")
        order_seq = []

    for name in order_seq:
        if name not in agents:
            warnings.append(f"Agent '{name}' is referenced in 'order' but not configured.")

    action_threshold = config.get("action_threshold")
    if action_threshold is not None:
        valid_levels = {"low", "medium", "high"}
        if str(action_threshold).lower() not in valid_levels:
            warnings.append(
                "Unknown action_threshold value '%s'. Expected one of: low, medium, high." % action_threshold
            )

    actions = config.get("actions")
    if actions is not None and not isinstance(actions, Mapping):
        errors.append("The 'actions' section must be a mapping of action names to settings.")

    return errors, warnings


def extract_providers(config: Mapping[str, Any]) -> List[str]:
    """Return a list of unique provider identifiers referenced by the configuration."""

    providers = []
    agents = _normalise_agents(config)
    for agent_cfg in agents.values():
        provider = agent_cfg.get("provider")
        if isinstance(provider, str):
            provider_key = provider.lower()
            if provider_key not in providers:
                providers.append(provider_key)
    return providers


def required_env_vars(config: Mapping[str, Any]) -> List[str]:
    """Return the environment variables required by providers in *config*."""

    providers = extract_providers(config)
    env_vars = {PROVIDER_ENV_VARS[p] for p in providers if p in PROVIDER_ENV_VARS}
    return sorted(env_vars)


def environment_status(
    env_vars: Iterable[str], env: Mapping[str, str] | None = None
) -> List[Dict[str, Any]]:
    """Return a list describing whether each environment variable is defined."""

    source = env or os.environ
    status: List[Dict[str, Any]] = []
    for var in sorted(env_vars):
        status.append({"variable": var, "present": bool(source.get(var))})
    return status


def missing_dependencies(config: Mapping[str, Any]) -> List[str]:
    """Return a sorted list of missing optional Python dependencies."""

    missing: set[str] = set()
    providers = extract_providers(config)
    for provider in providers:
        for dependency in PROVIDER_DEPENDENCIES.get(provider, ()):  # pragma: no branch
            if importlib_util.find_spec(dependency) is None:
                missing.add(dependency)
    return sorted(missing)


def build_offline_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a copy of *config* adjusted to use static offline responses."""

    offline = copy.deepcopy(dict(config))
    agents = _normalise_agents(offline)
    if not agents:
        agents = {}
    for name, default_response in OFFLINE_AGENT_RESPONSES.items():
        current = agents.get(name, {})
        updated: Dict[str, Any] = dict(current)
        updated["provider"] = "mock"
        if "response" not in updated:
            updated["response"] = copy.deepcopy(default_response)
        agents[name] = updated
    offline["agents"] = agents
    if "order" not in offline or not isinstance(offline.get("order"), Sequence):
        offline["order"] = list(DEFAULT_AGENT_ORDER)
    if "action_threshold" not in offline:
        offline["action_threshold"] = "medium"
    return offline

