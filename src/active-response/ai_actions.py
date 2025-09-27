"""Active response helper for invoking the WazAI Sentinel AI pipeline."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from ai_agents.pipeline import run_pipeline


def load_alert_from_stdin() -> Dict[str, Any]:
    data = sys.stdin.read()
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"raw": data}


def main() -> int:
    alert = load_alert_from_stdin()
    config_path = os.getenv("WAZAI_AI_CONFIG")
    enriched = run_pipeline(alert, config_path)
    print(json.dumps(enriched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
