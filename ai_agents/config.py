"""Configuration helpers for WazAI Sentinel AI agents."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None

DEFAULT_CONFIG_PATH = Path(os.getenv("WAZAI_AI_CONFIG", "etc/ai_config.yaml"))


def load_ai_config(config_path: os.PathLike | str | None = None) -> Dict[str, Any]:
    """Load AI configuration from YAML.

    Parameters
    ----------
    config_path
        Path to the configuration file. If not provided, :data:`DEFAULT_CONFIG_PATH`
        is used.

    Returns
    -------
    dict
        Parsed configuration dictionary. Empty dictionary if the file does not
        exist or cannot be parsed.
    """
    path = Path(config_path or DEFAULT_CONFIG_PATH)
    if not path.exists():
        return {}

    if yaml is None:
        return {}

    try:
        with path.open("r", encoding="utf-8") as handler:
            config = yaml.safe_load(handler) or {}
    except (OSError, yaml.YAMLError):
        return {}

    return config
