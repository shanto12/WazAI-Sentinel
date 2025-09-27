"""Supervisor agent coordinating the AI pipeline."""
from __future__ import annotations

import logging
import json
from collections.abc import Iterable
from typing import Any, Dict, List

from .agents import AGENT_REGISTRY
from .base import AgentContext
from .actions import ActionExecutor
from .clients import APIClientError

LOGGER = logging.getLogger("wazai.ai")


class SupervisorAgent:
    """High level orchestrator for the AI pipeline."""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.logger = LOGGER
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, self.config.get("log_level", "INFO")))

    def build_agents(self) -> List[Any]:
        context = AgentContext(config=self.config.get("agents", {}), logger=self.logger)
        order: Iterable[str] = self.config.get("order") or [
            "investigator",
            "triage",
            "enricher",
            "correlator",
            "responder",
        ]
        agents = []
        for name in order:
            if name not in AGENT_REGISTRY:
                self.logger.warning("Unknown agent '%s' in AI pipeline order", name)
                continue
            try:
                agents.append(AGENT_REGISTRY[name](context))
            except APIClientError as exc:
                self.logger.error("Failed to initialise agent %s: %s", name, exc)
        return agents

    def run(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Running AI pipeline for alert %s", alert.get("id", "<unknown>"))
        response = alert.copy()
        response.setdefault("ai", {})
        for agent in self.build_agents():
            try:
                response = agent.run(response)
            except APIClientError as exc:
                self.logger.error("Agent %s failed: %s", getattr(agent, "name", agent), exc)
                response.setdefault("ai_errors", []).append({
                    "agent": getattr(agent, "name", "unknown"),
                    "error": str(exc),
                })
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Unexpected error in agent %s", getattr(agent, "name", agent))
                response.setdefault("ai_errors", []).append({
                    "agent": getattr(agent, "name", "unknown"),
                    "error": str(exc),
                })
        return response

    def _parse_structured_output(self, value: Any) -> Dict[str, Any] | None:
        """Attempt to coerce *value* returned from an agent into a dictionary."""

        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return None
        content = value.strip()
        if not content:
            return None
        if content.startswith("```"):
            lines = content.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[0].strip().lower() == "json":
                lines = lines[1:]
            while lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            self.logger.debug("Failed to decode JSON from responder output: %s", content)
            return None
        return parsed if isinstance(parsed, dict) else None

    def _normalise_action(self, candidate: Any) -> Dict[str, Any] | None:
        """Normalise a single *candidate* action into the expected mapping."""

        if isinstance(candidate, dict):
            action_type = candidate.get("type")
            if action_type:
                payload = {"type": action_type}
                for key in ("channel", "reason", "summary", "system", "endpoint", "message", "parameters"):
                    if key in candidate:
                        payload[key] = candidate[key]
                if "reason" not in payload and candidate.get("justification"):
                    payload["reason"] = candidate["justification"]
                return payload
            if "action" in candidate and isinstance(candidate["action"], str):
                return {"type": candidate["action"], **{k: v for k, v in candidate.items() if k != "action"}}
        if isinstance(candidate, str) and candidate.strip():
            return {"type": candidate.strip()}
        return None

    def decide_actions(self, enriched_alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine follow-up actions using responder output with severity fallback."""

        actions: List[Dict[str, Any]] = []
        responder = enriched_alert.get("ai", {}).get("responder")
        parsed = self._parse_structured_output(responder)
        if parsed:
            raw_actions = parsed.get("actions") if isinstance(parsed.get("actions"), list) else None
            if raw_actions:
                for candidate in raw_actions:
                    normalised = self._normalise_action(candidate)
                    if normalised:
                        actions.append(normalised)
            elif parsed:
                normalised = self._normalise_action(parsed)
                if normalised:
                    actions.append(normalised)
        if actions:
            return actions

        severity = (
            enriched_alert.get("ai", {})
            .get("triage", {})
            if isinstance(enriched_alert.get("ai", {}).get("triage"), dict)
            else enriched_alert.get("ai", {}).get("triage")
        )
        severity_key = None
        if isinstance(severity, dict):
            severity_key = severity.get("severity")
        elif isinstance(severity, str):
            severity_key = severity
        if severity_key:
            threshold = self.config.get("action_threshold", "medium")
            levels = ["low", "medium", "high"]
            if severity_key.lower() not in levels:
                self.logger.warning("Unknown severity level '%s'", severity_key)
                return actions
            if threshold.lower() not in levels:
                self.logger.warning("Unknown action threshold '%s'", threshold)
                return actions
            if levels.index(severity_key.lower()) >= levels.index(threshold.lower()):
                actions.append({"type": "notify", "channel": "security_ops"})
        return actions

    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute *actions* via :class:`ActionExecutor` and return serialisable results."""

        if not actions:
            return []
        executor = ActionExecutor(
            config=self.config.get("actions", {}),
            logger=self.logger,
        )
        results: List[Dict[str, Any]] = []
        for result in executor.execute_many(actions):
            results.append(result.to_dict())
        return results
