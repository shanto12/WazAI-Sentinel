# WazAI Sentinel

**WazAI Sentinel** is an open-source AI-enhanced SIEM platform for automated threat detection,
triage, and response using large language models (LLMs). It builds on a mature open-source SIEM
foundation with a modern multi-agent architecture that enriches alerts in real time and drives
intelligent response actions across your estate.

## Key Capabilities

- **AI-assisted investigations** – A dedicated Investigator agent digests alerts and log entries,
  summarising findings and surfacing potential indicators of compromise (IOCs).
- **Automated triage** – Grok-powered triage quickly prioritises incidents by severity, ensuring
  that security teams focus on the threats that matter most.
- **Threat intelligence enrichment** – Enricher agents supplement alerts with contextual insights,
  campaign data, and recommended remediation steps.
- **Cross-incident correlation** – Correlator agents identify related events and emerging attack
  paths, enabling a proactive defence posture.
- **Active response** – Supervisor logic can trigger automated actions, such as isolating hosts or
  notifying SOC tooling when high-risk activity is detected.

## Architecture Overview

WazAI Sentinel retains proven collection agents, decoders, and a battle-tested rules engine while
introducing a new `ai_agents/` module that coordinates OpenAI and Grok large language models. The
pipeline is configured via `etc/ai_config.yaml`, allowing operators to tune models, prompts, and
decision thresholds.

```
Alert ingestion -> Investigator -> Triage -> Enricher -> Correlator -> Supervisor decisions
```

Supervisor decisions are exposed to the existing active response framework, enabling automated
containment workflows.

## Getting Started

1. **Create an isolated Python environment** – `python3 -m venv .venv && source .venv/bin/activate`
2. **Install dependencies** – `pip install -r framework/requirements.txt`
3. **Bootstrap configuration** – Generate a starter AI config (add `--offline` for demo mode):

   ```bash
   python -m ai_agents bootstrap --path etc/ai_config.yaml
   ```

4. **Run environment checks** – Verify required API keys and packages:

   ```bash
   python -m ai_agents doctor
   ```

5. **Provide API credentials** – Export OpenAI and Grok credentials before using live providers:

   ```bash
   export OPENAI_API_KEY="sk-..."
   export GROK_API_KEY="grok-..."
   ```

6. **Simulate the pipeline** – Enrich a sample alert (add `--offline` to avoid external calls):

   ```bash
   python -m ai_agents run extensions/ai/sample_alert.json --pretty
   ```

7. **Deploy** – Launch the manager and agents as you would with traditional deployments.
   New AI insights will appear in stored alerts and in dashboard visualisations.

## Documentation

- [`docs/ai_agents.md`](docs/ai_agents.md) – Detailed agent behaviours and integration points.
- [`extensions/ai/`](extensions/ai/) – Sample scripts and utilities for validating AI workflows.
- [`ruleset/`](ruleset/) – Decoder and rule additions that trigger the AI pipeline.

## Licensing

WazAI Sentinel is released under the GNU General Public License version 2 (GPLv2). This project is
an independent fork of an earlier open-source SIEM codebase and is not affiliated with its previous
maintainers. Please consult the [`LICENSE`](LICENSE) file for full terms and fork attribution.

## Community

We welcome contributions focused on AI-assisted security analytics, automation, and observability.
Please open issues or submit pull requests to help shape the future of WazAI Sentinel.
