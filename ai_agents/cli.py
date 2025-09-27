"""Command line entry point for WazAI Sentinel AI tooling."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

from .config import DEFAULT_CONFIG_PATH, load_ai_config
from .diagnostics import (
    build_offline_config,
    environment_status,
    missing_dependencies,
    required_env_vars,
    validate_config,
)
from .pipeline import run_pipeline
from .templates import DEFAULT_CONFIG_TEMPLATE

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None


def _dump_config(config: Dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(config, sort_keys=False)
    return json.dumps(config, indent=2)


def _load_alert(path: str | None) -> Dict[str, Any]:
    if not path or path == "-":
        return json.loads(sys.stdin.read())
    data = Path(path).read_text(encoding="utf-8")
    return json.loads(data)


def _print_diagnostics(result: Dict[str, Any]) -> None:
    print("Configuration:")
    if result["config_path_exists"]:
        print(f"  path: {result['config_path']}")
    else:
        print(f"  path: {result['config_path']} (missing, using defaults)")
    if result["errors"]:
        print("  errors:")
        for item in result["errors"]:
            print(f"    - {item}")
    if result["warnings"]:
        print("  warnings:")
        for item in result["warnings"]:
            print(f"    - {item}")
    print("")
    print("Environment:")
    if result["env"]:
        for entry in result["env"]:
            status = "present" if entry["present"] else "missing"
            print(f"  {entry['variable']}: {status}")
    else:
        print("  No API keys required for the current configuration.")
    if result["dependencies"]:
        print("")
        print("Missing Python packages:")
        for package in result["dependencies"]:
            print(f"  - {package}")


def command_bootstrap(args: argparse.Namespace) -> int:
    destination = Path(args.path or DEFAULT_CONFIG_PATH)
    if destination.exists() and not args.force:
        print(f"Configuration already exists at {destination}. Use --force to overwrite.")
        return 1

    config = copy.deepcopy(DEFAULT_CONFIG_TEMPLATE)
    if args.offline:
        config = build_offline_config(config)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_dump_config(config), encoding="utf-8")
    print(f"Wrote WazAI Sentinel AI configuration to {destination}")
    if args.offline:
        print("Offline mode enabled: generated static responses for all agents.")
    else:
        print("Remember to export OPENAI_API_KEY and GROK_API_KEY before running the pipeline.")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    config_path = Path(args.config or DEFAULT_CONFIG_PATH)
    config_data = load_ai_config(config_path)
    effective_config = config_data or copy.deepcopy(DEFAULT_CONFIG_TEMPLATE)
    errors, warnings = validate_config(config_data)
    env_vars = required_env_vars(effective_config)
    env_status = environment_status(env_vars)
    missing = missing_dependencies(effective_config)

    result = {
        "config_path": str(config_path),
        "config_path_exists": config_path.exists(),
        "errors": errors,
        "warnings": warnings,
        "env": env_status,
        "dependencies": missing,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_diagnostics(result)

    return 0 if not errors else 2


def command_run(args: argparse.Namespace) -> int:
    config_path = Path(args.config) if args.config else None
    config_data = load_ai_config(config_path) if config_path else {}
    if not config_data:
        config_data = copy.deepcopy(DEFAULT_CONFIG_TEMPLATE)
    if args.offline:
        config_data = build_offline_config(config_data)

    alert = _load_alert(args.alert)
    enriched = run_pipeline(alert, config=config_data)

    output = json.dumps(enriched, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wazai",
        description="Utilities for managing the WazAI Sentinel AI pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="Generate a starter ai_config.yaml file.",
    )
    bootstrap.add_argument(
        "--path",
        "-p",
        help="Destination path for the generated configuration (default: etc/ai_config.yaml).",
    )
    bootstrap.add_argument(
        "--offline",
        action="store_true",
        help="Produce a configuration that uses static responses instead of live API calls.",
    )
    bootstrap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing configuration file.",
    )
    bootstrap.set_defaults(func=command_bootstrap)

    doctor = subparsers.add_parser(
        "doctor",
        help="Inspect configuration, dependencies, and API keys.",
    )
    doctor.add_argument(
        "--config",
        "-c",
        help="Path to the ai_config.yaml file (default: etc/ai_config.yaml).",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Return diagnostics as JSON for automation.",
    )
    doctor.set_defaults(func=command_doctor)

    run = subparsers.add_parser(
        "run",
        help="Execute the AI pipeline for an alert JSON payload.",
    )
    run.add_argument(
        "alert",
        help="Path to the alert JSON file. Use '-' to read from stdin.",
    )
    run.add_argument(
        "--config",
        "-c",
        help="Path to the ai_config.yaml file (default: etc/ai_config.yaml).",
    )
    run.add_argument(
        "--offline",
        action="store_true",
        help="Ignore live providers and use offline static responses.",
    )
    run.add_argument(
        "--output",
        "-o",
        help="Write the enriched alert to this file instead of stdout.",
    )
    run.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    run.set_defaults(func=command_run)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

