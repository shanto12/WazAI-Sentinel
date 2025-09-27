"""Supervisor agent coordinating the AI pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from .agents import AGENT_REGISTRY
from .base import AgentContext
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

    def decide_actions(self, enriched_alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine follow-up actions based on thresholds."""
        actions: List[Dict[str, Any]] = []
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
