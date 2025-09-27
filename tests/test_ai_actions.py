"""Unit tests for the AI-driven action workflow."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_agents.actions import ActionExecutor, ActionExecutionError
from ai_agents.supervisor import SupervisorAgent


def test_action_executor_notify() -> None:
    executor = ActionExecutor(config={"notify": {"channel": "blue_team"}})
    result = executor.execute({"type": "notify", "message": "Check alert"})
    assert result.type == "notify"
    assert result.status == "queued"
    assert result.details["channel"] == "blue_team"


def test_action_executor_disabled_action() -> None:
    executor = ActionExecutor(config={"isolate_endpoint": {"enabled": False}})
    result = executor.execute({"type": "isolate_endpoint", "endpoint": "host-1"})
    assert result.status == "skipped"
    assert result.details["reason"] == "disabled"


@pytest.mark.parametrize(
    "payload,expected",
    [
        ("""{"actions": [{"type": "notify", "channel": "soc"}]}""", "notify"),
        ("""```json\n{\n  \"actions\": [{\"type\": \"create_ticket\"}]}\n```""", "create_ticket"),
    ],
)
def test_decide_actions_parses_structured_output(payload: str, expected: str) -> None:
    supervisor = SupervisorAgent({"log_level": "CRITICAL"})
    enriched = {"ai": {"responder": payload}}
    actions = supervisor.decide_actions(enriched)
    assert actions[0]["type"] == expected


def test_decide_actions_fallback_severity() -> None:
    supervisor = SupervisorAgent({"log_level": "CRITICAL", "action_threshold": "low"})
    enriched = {"ai": {"triage": {"severity": "high"}}}
    actions = supervisor.decide_actions(enriched)
    assert actions == [{"type": "notify", "channel": "security_ops"}]


def test_execute_actions_returns_serialisable() -> None:
    supervisor = SupervisorAgent({"log_level": "CRITICAL"})
    actions = [{"type": "notify", "channel": "soc", "message": "Ping"}]
    results = supervisor.execute_actions(actions)
    assert isinstance(results, list)
    assert results[0]["type"] == "notify"
    json.dumps(results)


def test_executor_requires_type() -> None:
    executor = ActionExecutor()
    with pytest.raises(ActionExecutionError):
        executor.execute({"message": "missing type"})
