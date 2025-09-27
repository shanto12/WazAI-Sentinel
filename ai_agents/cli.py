"""Command line entry point for WazAI Sentinel AI tooling."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

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


MODEL_CATALOG: Dict[str, Dict[str, Sequence[Tuple[str, str]]]] = {
    "openai": {
        "label": "OpenAI",
        "models": (
            ("gpt-4.1", "GPT-4.1 (flagship reasoning)"),
            ("gpt-4.1-mini", "GPT-4.1 Mini (cost optimised)"),
            ("o3-mini", "o3 Mini (structured reasoning)"),
        ),
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "models": (
            ("claude-3.5-sonnet", "Claude 3.5 Sonnet (balanced)"),
            ("claude-3.5-haiku", "Claude 3.5 Haiku (fast)"),
        ),
    },
    "grok": {
        "label": "Grok",
        "models": (
            ("grok-2", "Grok 2 (latest general model)"),
            ("grok-beta", "Grok Beta (legacy compatibility)"),
        ),
    },
    "google": {
        "label": "Google Gemini",
        "models": (
            ("gemini-1.5-pro", "Gemini 1.5 Pro (multimodal capable)"),
            ("gemini-1.5-flash", "Gemini 1.5 Flash (low latency)"),
        ),
    },
}

AGENT_TASK_DESCRIPTIONS: Dict[str, str] = {
    "investigator": "Investigate alerts and summarise key findings",
    "triage": "Assign severity and justification",
    "enricher": "Add contextual threat intelligence",
    "correlator": "Cross-reference with historical incidents",
    "responder": "Propose incident response actions",
}


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
        print(
            "Remember to export OPENAI_API_KEY, GROK_API_KEY, ANTHROPIC_API_KEY, or "
            "GOOGLE_API_KEY as required before running the pipeline."
        )
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


def _prompt_choice(
    title: str,
    options: Sequence[Tuple[str, str]],
    default: str | None = None,
    allow_custom: bool = False,
) -> str:
    """Prompt the user to select one of the provided *options*."""

    enumerated: List[Tuple[int, str, str]] = []
    for index, (value, description) in enumerate(options, start=1):
        enumerated.append((index, value, description))

    if allow_custom:
        enumerated.append((len(enumerated) + 1, "__custom__", "Custom value"))

    default_label = f" [{default}]" if default else ""
    while True:
        print(title)
        for idx, value, description in enumerated:
            marker = "*" if default and value == default else " "
            print(f"  {idx}. {description} ({value}){marker}")
        choice = input(f"Enter selection{default_label}: ").strip()
        if not choice and default:
            return default
        if choice.isdigit():
            idx = int(choice)
            for number, value, _ in enumerated:
                if number == idx:
                    if value == "__custom__":
                        custom = input("Enter custom value: ").strip()
                        if custom:
                            return custom
                        break
                    return value
        else:
            for _, value, _ in enumerated:
                if choice.lower() == value.lower():
                    return value
        print("Invalid selection. Please choose one of the listed options.")


def _prompt_yes_no(prompt: str, default: bool = False) -> bool:
    yes_values = {"y", "yes"}
    no_values = {"n", "no"}
    default_label = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} ({default_label}): ").strip().lower()
        if not response:
            return default
        if response in yes_values:
            return True
        if response in no_values:
            return False
        print("Please respond with 'y' or 'n'.")


def command_configure(args: argparse.Namespace) -> int:
    config_path = Path(args.config or DEFAULT_CONFIG_PATH)
    existing = load_ai_config(config_path)
    config = existing or copy.deepcopy(DEFAULT_CONFIG_TEMPLATE)
    if "agents" not in config:
        config["agents"] = {}

    print("\n=== WazAI Sentinel AI configuration ===")
    print(
        "Select the AI provider and model for each agent task. "
        "Press Enter to keep the current value.\n"
    )

    agents = config.get("agents", {})
    provider_options = [
        (provider, data["label"])
        for provider, data in MODEL_CATALOG.items()
    ]

    for agent_name, agent_config in agents.items():
        task_description = AGENT_TASK_DESCRIPTIONS.get(agent_name, agent_name)
        print(f"--- {agent_name.title()} ({task_description}) ---")
        current_provider = str(agent_config.get("provider", "openai"))
        provider_choices = list(provider_options)
        if current_provider not in MODEL_CATALOG:
            provider_choices.append((current_provider, f"Current provider ({current_provider})"))
        provider = _prompt_choice(
            "Select AI provider:",
            provider_choices,
            default=current_provider,
            allow_custom=True,
        )
        agent_config["provider"] = provider

        model_list = MODEL_CATALOG.get(provider, {}).get("models", ())
        current_model = str(agent_config.get("model", ""))
        model_choices: List[Tuple[str, str]] = list(model_list)
        known_models = {value for value, _ in model_list}
        if current_model and current_model not in known_models:
            model_choices.append((current_model, f"Current model ({current_model})"))
        if not model_choices:
            model_choices.append((current_model or provider, f"Default model for {provider}"))
        model = _prompt_choice(
            "Select model:",
            model_choices,
            default=current_model or model_choices[0][0],
            allow_custom=True,
        )
        agent_config["model"] = model

        if _prompt_yes_no("Would you like to edit the prompt?", default=False):
            print("Enter the new prompt text. Use {data} as a placeholder for alert JSON.")
            new_prompt = input("Prompt: ").strip()
            if new_prompt:
                agent_config["prompt"] = new_prompt

        print("")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_dump_config(config), encoding="utf-8")

    print(f"Saved updated configuration to {config_path}")
    print("Run 'wazai doctor' to verify environment variables and dependencies.\n")
    return 0


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

    configure = subparsers.add_parser(
        "configure",
        help="Interactively choose AI providers, models, and prompts for each agent.",
    )
    configure.add_argument(
        "--config",
        "-c",
        help="Path to the ai_config.yaml file (default: etc/ai_config.yaml).",
    )
    configure.set_defaults(func=command_configure)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

