"""Action execution primitives for the WazAI Sentinel AI workflow."""
from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, MutableMapping
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


class ActionExecutionError(RuntimeError):
    """Raised when an action cannot be executed."""


@dataclass
class ActionResult:
    """Represents the outcome of executing an action."""

    type: str
    status: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the result."""

        payload: Dict[str, Any] = {"type": self.type, "status": self.status}
        if self.details:
            payload["details"] = self.details
        return payload


ActionHandler = Callable[[MutableMapping[str, Any], MutableMapping[str, Any], logging.Logger], ActionResult]


def _notify_security_ops(
    action: MutableMapping[str, Any], config: MutableMapping[str, Any], logger: logging.Logger
) -> ActionResult:
    channel = action.get("channel") or config.get("channel") or "security_ops"
    message = action.get("message") or config.get("message") or "Automated notification from WazAI Sentinel."
    logger.info("Queuing notification for channel '%s': %s", channel, message)
    return ActionResult(
        type="notify",
        status="queued",
        details={"channel": channel, "message": message},
    )


def _create_ticket(
    action: MutableMapping[str, Any], config: MutableMapping[str, Any], logger: logging.Logger
) -> ActionResult:
    system = action.get("system") or config.get("system") or "jira"
    summary = action.get("summary") or config.get("summary") or "Automated incident ticket"
    ticket_id = action.get("ticket_id") or f"IR-{uuid.uuid4().hex[:8]}"
    logger.info("Preparing ticket %s in %s with summary '%s'", ticket_id, system, summary)
    return ActionResult(
        type="create_ticket",
        status="created",
        details={
            "system": system,
            "summary": summary,
            "ticket_id": ticket_id,
        },
    )


def _isolate_endpoint(
    action: MutableMapping[str, Any], config: MutableMapping[str, Any], logger: logging.Logger
) -> ActionResult:
    endpoint = action.get("endpoint") or config.get("endpoint")
    if not endpoint:
        raise ActionExecutionError("Isolate endpoint action requires an 'endpoint' value")
    logger.warning("Scheduling network isolation for endpoint %s", endpoint)
    return ActionResult(
        type="isolate_endpoint",
        status="queued",
        details={"endpoint": endpoint},
    )


DEFAULT_ACTIONS: Dict[str, ActionHandler] = {
    "notify": _notify_security_ops,
    "create_ticket": _create_ticket,
    "isolate_endpoint": _isolate_endpoint,
}


class ActionExecutor:
    """Executes high-level actions decided by the AI agents."""

    def __init__(
        self,
        config: Optional[MutableMapping[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        *,
        registry: Optional[Dict[str, ActionHandler]] = None,
    ) -> None:
        self.config = config or {}
        self.logger = logger or logging.getLogger("wazai.actions")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.registry: Dict[str, ActionHandler] = dict(DEFAULT_ACTIONS)
        if registry:
            self.registry.update(registry)

    def register_action(self, name: str, handler: ActionHandler) -> None:
        """Register or override the handler for *name*."""

        self.registry[name] = handler

    def execute(self, action: MutableMapping[str, Any]) -> ActionResult:
        """Execute a single *action* mapping and return an :class:`ActionResult`."""

        if isinstance(action, str):
            action = {"type": action}  # type: ignore[assignment]
        if not isinstance(action, MutableMapping):  # pragma: no cover - defensive
            raise ActionExecutionError("Action must be a mapping of parameters")
        action_type = action.get("type")
        if not action_type:
            raise ActionExecutionError("Action payload is missing the 'type' key")
        cfg = self.config.get(action_type, {})
        if isinstance(cfg, MutableMapping) and not cfg.get("enabled", True):
            self.logger.info("Skipping disabled action '%s'", action_type)
            return ActionResult(
                type=action_type,
                status="skipped",
                details={"reason": "disabled"},
            )
        handler = self.registry.get(action_type)
        if not handler:
            raise ActionExecutionError(f"No handler registered for action type '{action_type}'")
        # Ensure configuration is a mapping for handler compatibility
        if not isinstance(cfg, MutableMapping):
            cfg = {}
        return handler(action, cfg, self.logger)

    def execute_many(self, actions: Iterable[MutableMapping[str, Any]]) -> List[ActionResult]:
        """Execute all *actions* sequentially and collect their results."""

        results: List[ActionResult] = []
        for action in actions:
            try:
                results.append(self.execute(action))
            except ActionExecutionError as exc:
                self.logger.error("Failed to execute action %s: %s", action, exc)
                results.append(
                    ActionResult(
                        type=action.get("type", "unknown"),
                        status="failed",
                        details={"error": str(exc)},
                    )
                )
        return results


__all__ = ["ActionExecutionError", "ActionExecutor", "ActionResult", "DEFAULT_ACTIONS"]
