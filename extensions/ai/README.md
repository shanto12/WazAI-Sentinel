# WazAI Sentinel AI Extensions

This directory hosts helper utilities and examples for integrating the WazAI Sentinel
AI pipeline with external systems.

## Files

- `simulate_alert.py` – Runs the AI pipeline locally using sample alert data. Useful
  for validating API connectivity and reviewing AI enrichment responses.
- `sample_alert.json` – Example alert payload used by the simulation script.

## Usage

Export valid API keys before running the simulator (or use `--offline` to avoid remote calls):

```bash
export OPENAI_API_KEY=your_openai_key
export GROK_API_KEY=your_grok_key
python -m ai_agents run extensions/ai/sample_alert.json --pretty
```

You can still run the original helper script directly:

```bash
python3 extensions/ai/simulate_alert.py --offline
```
