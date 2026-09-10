"""Thin LLM client used for planning and narrative synthesis.

The copilot does not depend on this being configured. When no API key is set
`available` is False and callers fall back to their deterministic path; the
agent pipeline, its tools and its data analysis run identically either way.
"""

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    pass


class LLMClient:
    @property
    def available(self) -> bool:
        return settings.llm_enabled

    @property
    def provider(self) -> str:
        return settings.llm_provider.lower()

    def complete(self, *, system: str, prompt: str, max_tokens: int = 1200) -> str:
        if not self.available:
            raise LLMUnavailable("No LLM API key configured")
        if self.provider == "openai":
            return self._openai(system, prompt, max_tokens)
        return self._anthropic(system, prompt, max_tokens)

    def complete_json(self, *, system: str, prompt: str, max_tokens: int = 1200) -> dict:
        raw = self.complete(system=system, prompt=prompt, max_tokens=max_tokens).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json").strip()
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise LLMUnavailable("Model did not return JSON")
        return json.loads(raw[start:end + 1])

    def _anthropic(self, system: str, prompt: str, max_tokens: int) -> str:
        base = settings.llm_base_url or "https://api.anthropic.com"
        r = httpx.post(
            f"{base}/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=settings.llm_timeout_seconds,
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []))

    def _openai(self, system: str, prompt: str, max_tokens: int) -> str:
        base = settings.llm_base_url or "https://api.openai.com"
        r = httpx.post(
            f"{base}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_completion_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=settings.llm_timeout_seconds,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


llm_client = LLMClient()
