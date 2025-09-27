"""API clients used by the WazAI Sentinel AI agents."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


class APIClientError(RuntimeError):
    """Raised when an upstream AI provider returns an error."""


class OpenAIClient:
    """Minimal OpenAI client used for prompt completion."""

    api_url = "https://api.openai.com/v1/chat/completions"

    def __init__(self, model: str) -> None:
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise APIClientError("OPENAI_API_KEY environment variable is not set.")

    def complete(self, prompt: str, *, temperature: float = 0.1) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an AI security analyst."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        response = requests.post(
            self.api_url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        if response.status_code >= 400:
            raise APIClientError(
                f"OpenAI API error {response.status_code}: {response.text}"
            )
        data: Dict[str, Any] = response.json()
        return data["choices"][0]["message"]["content"].strip()


class GrokClient:
    """Wrapper around the xAI Grok API for triage."""

    api_url = "https://api.x.ai/v1/chat/completions"

    def __init__(self, model: str) -> None:
        self.model = model
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise APIClientError("GROK_API_KEY environment variable is not set.")

    def complete(self, prompt: str, *, temperature: float = 0.1) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an incident triage specialist."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        response = requests.post(
            self.api_url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        if response.status_code >= 400:
            raise APIClientError(
                f"Grok API error {response.status_code}: {response.text}"
            )
        data: Dict[str, Any] = response.json()
        return data["choices"][0]["message"]["content"].strip()


def build_client(provider: str, model: str) -> Optional[object]:
    """Factory returning the correct API client for *provider*."""
    if provider.lower() == "openai":
        return OpenAIClient(model)
    if provider.lower() == "grok":
        return GrokClient(model)
    return None
