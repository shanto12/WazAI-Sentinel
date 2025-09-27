# WazAI Sentinel Autonomous Incident Response Workflow

This document describes the revamped AI-driven workflow that powers WazAI Sentinel's
security alert triage and incident response automation.

## Pipeline overview

The AI pipeline is orchestrated by the `SupervisorAgent`, which creates a chain of
specialised agents defined in `etc/ai_config.yaml`. Each agent consumes the evolving
alert payload and appends its own analysis. The default workflow consists of:

1. **Investigator** – summarises the alert and highlights impacted assets and risk.
2. **Triage** – assigns a severity level and justification.
3. **Enricher** – injects contextual threat intelligence and recommended mitigations.
4. **Correlator** – finds related historical events or ongoing campaigns.
5. **Responder** – synthesises a concrete action plan aligned with organisational
   playbooks.

The order and configuration of these agents can be customised through the YAML file
without modifying code.

## Action planning and execution

The new `Responder` agent focuses on generating structured action recommendations. Its
output is parsed by the supervisor to build a list of normalised action dictionaries.
These are then evaluated against severity-based safeguards to ensure sensible defaults
when the AI response is incomplete.

Actions are executed via the `ActionExecutor` abstraction. The executor ships with
handlers for:

- Sending notifications to security operations channels.
- Creating incident tickets in tracking systems such as Jira or ServiceNow.
- Scheduling endpoint isolation tasks.

Each handler records its activity via the central logger, returns structured metadata
for auditing, and respects configuration flags (for example, disabling isolation in
non-production environments).

## Configuration

Key settings live in `etc/ai_config.yaml`:

- `order` defines the agent execution order.
- `agents` configures provider/model/prompt overrides for each agent.
- `actions` toggles or configures downstream execution modules (channels, ticketing
  systems, and more).

Because the executor is registry-driven, additional handlers can be injected at
runtime or through future extensions without touching the supervisor logic.

## Extending the workflow

- Implement new agent classes in `ai_agents/agents.py` and add them to
  `AGENT_REGISTRY`.
- Register custom action handlers via `ActionExecutor.register_action` or by updating
  the configuration registry.
- Wrap the `run_pipeline` helper to integrate the AI workflow with alert ingestion
  services, messaging queues, or response platforms.

The goal of these changes is to provide a secure, autonomous foundation for
AI-assisted incident response while keeping the system adaptable to new tooling and
operational constraints.
