"""Simulate running the WazAI Sentinel AI pipeline on a sample alert."""
from __future__ import annotations

import json
from pathlib import Path

from ai_agents.pipeline import run_pipeline

SAMPLE_PATH = Path(__file__).with_name("sample_alert.json")


def main() -> None:
    alert = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    enriched = run_pipeline(alert)
    print(json.dumps(enriched, indent=2))


if __name__ == "__main__":
    main()
