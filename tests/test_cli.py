"""Tests for the ai_agents CLI utilities."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_agents import cli  # noqa: E402
try:  # pragma: no cover - optional dependency
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def test_bootstrap_offline_generates_mock_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destination = tmp_path / "ai.yaml"
    exit_code = cli.main(["bootstrap", "--path", str(destination), "--offline"])
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Offline mode" in captured
    raw = destination.read_text(encoding="utf-8")
    if yaml is not None:
        config = yaml.safe_load(raw)
    else:
        config = json.loads(raw)
    assert config["agents"]["triage"]["provider"] == "mock"


def test_doctor_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / "ai.yaml"
    cli.main(["bootstrap", "--path", str(config_path), "--offline"])
    capsys.readouterr()
    exit_code = cli.main(["doctor", "--config", str(config_path), "--json"])
    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["config_path"] == str(config_path)
    assert payload["errors"] == []
    if payload["warnings"]:
        assert payload["warnings"] == [
            "Configuration file not found or empty; defaults will be used when running the pipeline."
        ]


def test_run_offline_outputs_enriched_alert(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    alert_path = tmp_path / "alert.json"
    alert_path.write_text(json.dumps({"id": "demo", "rule": {"description": "test"}}), encoding="utf-8")
    exit_code = cli.main(["run", str(alert_path), "--offline", "--pretty"])
    assert exit_code == 0
    output = capsys.readouterr().out
    enriched = json.loads(output)
    assert "ai" in enriched
    assert enriched["ai_actions"]


def test_configure_interactive_updates_models_and_prompts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "ai.yaml"
    responses = iter(
        [
            "1",  # investigator provider -> OpenAI
            "2",  # investigator model -> gpt-4.1-mini
            "n",  # investigator prompt unchanged
            "2",  # triage provider -> Anthropic
            "1",  # triage model -> claude-3.5-sonnet
            "y",  # triage prompt edit
            "Review severity {data}",
            "4",  # enricher provider -> Google Gemini
            "1",  # enricher model -> gemini-1.5-pro
            "n",  # enricher prompt unchanged
            "3",  # correlator provider -> Grok
            "1",  # correlator model -> grok-2
            "n",  # correlator prompt unchanged
            "1",  # responder provider -> OpenAI
            "1",  # responder model -> gpt-4.1
            "n",  # responder prompt unchanged
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    exit_code = cli.main(["configure", "--config", str(config_path)])
    assert exit_code == 0
    capsys.readouterr()  # drain output

    raw = config_path.read_text(encoding="utf-8")
    if yaml is not None:
        config = yaml.safe_load(raw)
    else:
        config = json.loads(raw)

    assert config["agents"]["investigator"]["model"] == "gpt-4.1-mini"
    assert config["agents"]["triage"]["provider"] == "anthropic"
    assert config["agents"]["triage"]["prompt"] == "Review severity {data}"
    assert config["agents"]["enricher"]["model"] == "gemini-1.5-pro"
