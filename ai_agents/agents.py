"""Concrete agent implementations."""
from __future__ import annotations

import json
from typing import Any, Dict

from .base import Agent, AgentContext
from .clients import APIClientError, build_client
try:
    from langchain_core.prompts import PromptTemplate
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    class PromptTemplate:  # type: ignore[too-few-public-methods]
        """Lightweight stand-in for :class:`langchain` prompt templates."""

        def __init__(self, template: str) -> None:
            self.template = template

        @classmethod
        def from_template(cls, template: str) -> "PromptTemplate":
            return cls(template)

        def format(self, **kwargs: str) -> str:
            return self.template.format(**kwargs)


class BaseAIChainAgent:
    """Base class with helper utilities for AI-backed agents."""

    name = "base"
    provider = "openai"
    model = "gpt-4o"
    prompt_template = ""

    def __init__(self, context: AgentContext) -> None:
        self.context = context
        self.client = None
        self.template = None
        self._build_client()
        self._build_prompt_template()

    def _build_client(self) -> None:
        provider = self.provider
        model = self.model
        cfg = self.context.config.get(self.name, {})
        provider = cfg.get("provider", provider)
        model = cfg.get("model", model)
        client = build_client(provider, model, settings=cfg)
        if client is None:
            raise APIClientError(f"Unsupported AI provider '{provider}' for agent {self.name}")
        self.client = client

    def _build_prompt_template(self) -> None:
        cfg = self.context.config.get(self.name, {})
        template = cfg.get("prompt", self.prompt_template)
        if template:
            self.template = PromptTemplate.from_template(template)
        else:
            self.template = None

    def _format_prompt(self, payload: Dict[str, Any]) -> str:
        body = {
            "payload": payload,
            "agent": self.name,
        }
        if self.template:
            return self.template.format(data=json.dumps(body, indent=2))
        return json.dumps(body, indent=2)

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._format_prompt(payload)
        result = self.client.complete(prompt)
        payload.setdefault("ai", {})[self.name] = result
        self.context.logger.debug("%s result: %s", self.name, result)
        return payload


class InvestigatorAgent(BaseAIChainAgent):
    name = "investigator"
    prompt_template = (
        "Analyze the following alert payload and summarize threats, impacted assets, "
        "and indicators. Provide JSON output with keys summary, findings, risk."
    )


class TriageAgent(BaseAIChainAgent):
    name = "triage"
    provider = "grok"
    model = "grok-beta"
    prompt_template = (
        "Classify the incident severity as high, medium, or low and justify. Return JSON "
        "with keys severity and justification."
    )


class EnricherAgent(BaseAIChainAgent):
    name = "enricher"
    prompt_template = (
        "Add threat intelligence context for the alert including known campaigns, "
        "recommended actions, and references. Return JSON with keys intel, actions, references."
    )


class CorrelatorAgent(BaseAIChainAgent):
    name = "correlator"
    prompt_template = (
        "Correlate this alert with historical events and list any related incident IDs, "
        "patterns, or lateral movement signals. Return JSON with keys correlations and notes."
    )


class ResponderAgent(BaseAIChainAgent):
    name = "responder"
    prompt_template = (
        "Using the investigation, triage, enrichment, and correlation results, "
        "recommend concrete incident response actions. Respond in JSON with keys "
        "actions (list of objects with type, reason, and parameters) and policy (string)."
    )


class Investigator(InvestigatorAgent, Agent):
    ...


class Triage(TriageAgent, Agent):
    ...


class Enricher(EnricherAgent, Agent):
    ...


class Correlator(CorrelatorAgent, Agent):
    ...


class Responder(ResponderAgent, Agent):
    ...


AGENT_REGISTRY = {
    "investigator": Investigator,
    "triage": Triage,
    "enricher": Enricher,
    "correlator": Correlator,
    "responder": Responder,
}
