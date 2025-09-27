# WazAI Sentinel AI Agents

WazAI Sentinel introduces a modular AI pipeline designed to analyse alerts, triage incidents, and
orchestrate automated responses. The pipeline is composed of four primary agents managed by a
Supervisor controller.

## Agents

### Investigator
- **Purpose**: Collects the initial alert or log payload and performs a first-pass analysis.
- **Model**: OpenAI (default `gpt-4o`).
- **Output**: Summary of suspicious activity, impacted assets, and key findings.

### Triage
- **Purpose**: Assigns a severity level and justification to help responders prioritise.
- **Model**: Grok (default `grok-beta`).
- **Output**: JSON with `severity` and `justification` fields.

### Enricher
- **Purpose**: Augments the alert with external threat intelligence and remediation guidance.
- **Model**: OpenAI (`gpt-4o`).
- **Output**: Contextual intel, recommended actions, and references.

### Correlator
- **Purpose**: Links the current alert with related historical events or campaigns.
- **Model**: OpenAI (`gpt-4o`).
- **Output**: Correlated incident IDs and notable patterns.

## Supervisor Workflow

1. Loads configuration from `etc/ai_config.yaml` or the `WAZAI_AI_CONFIG` environment variable.
2. Instantiates the agents in the configured order.
3. Executes each agent sequentially, enriching the alert payload.
4. Applies decision logic to determine automated responses (notify, block, isolate, etc.).
5. Returns the enriched alert and recommended actions to analysisd or downstream consumers.

## Integration Points

- **Decoders & Rules**: `ruleset/decoders/0900-ai_agents_decoders.xml` and
  `ruleset/rules/0900-ai_agents_rules.xml` introduce a dedicated trigger that routes matching
  events through the AI pipeline.
- **Active Response**: `src/active-response/ai_actions.py` exposes a CLI entry point that reads an
  alert from stdin, enriches it, and prints JSON suitable for chained scripts.
- **Extensions**: `extensions/ai/` contains runnable examples for validating connectivity and
  reviewing AI-generated insights.

## Configuration

The AI pipeline is controlled via YAML:

```yaml
log_level: INFO
action_threshold: medium
order:
  - investigator
  - triage
  - enricher
  - correlator
agents:
  investigator:
    provider: openai
    model: gpt-4o
    prompt: |
      You are WazAI Sentinel's Investigator... Data: {data}
```

Use environment variables to securely pass API keys:

```bash
export OPENAI_API_KEY="sk-..."
export GROK_API_KEY="grok-..."
```

### Tooling

- `python -m ai_agents bootstrap` – Generate a starter `ai_config.yaml`
  (add `--offline` for deterministic mock responses).
- `python -m ai_agents doctor` – Validate configuration structure, API keys,
  and optional Python dependencies.
- `python -m ai_agents run <alert.json>` – Execute the pipeline for a given
  alert payload. Combine with `--offline` to exercise the workflow without
  external API calls.

## Error Handling

- Missing API keys raise `APIClientError` and are recorded in the enriched alert payload under
  `ai_errors`.
- HTTP errors and unexpected exceptions are logged via the shared supervisor logger.
- Pipeline execution continues even if a single agent fails, ensuring partial insights are retained.

## Dashboard Enhancements

WazAI Sentinel dashboards should ingest the `ai` and `ai_actions` fields attached to alerts to build
visualisations for severity distribution, action frequency, and enrichment coverage.
