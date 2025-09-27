"""Simulate running the WazAI Sentinel AI pipeline on a sample alert."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from ai_agents.config import load_ai_config
from ai_agents.diagnostics import build_offline_config
from ai_agents.pipeline import run_pipeline
from ai_agents.templates import DEFAULT_CONFIG_TEMPLATE

SAMPLE_PATH = Path(__file__).with_name("sample_alert.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        default=str(SAMPLE_PATH),
        help="Path to an alert JSON payload (default: sample_alert.json).",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to ai_config.yaml (defaults to etc/ai_config.yaml).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use static responses instead of calling external providers.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Write enriched alert JSON to this path instead of stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    alert_path = Path(args.input)
    alert = json.loads(alert_path.read_text(encoding="utf-8"))

    config = load_ai_config(args.config)
    if not config:
        config = copy.deepcopy(DEFAULT_CONFIG_TEMPLATE)
    if args.offline:
        config = build_offline_config(config)

    enriched = run_pipeline(alert, config=config)
    output = json.dumps(enriched, indent=2 if args.pretty else None)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover - convenience script
    raise SystemExit(main())
