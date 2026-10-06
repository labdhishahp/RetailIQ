"""LLM client used for the agent runtime and narrative summaries.

The copilot does not depend on this being configured. When no API key is set
`available` is False and callers fall back to their deterministic path: the
agents still choose tools from what they observe, but by rule, not by model.

Tool calling (what makes the agents model-driven) goes through
create_message: the Anthropic SDK by default, or, with LLM_PROVIDER=openai,
the OpenAI Responses adapter in llm_providers.py. Callers see one contract
either way, so the agents, runtime and orchestrator are provider-agnostic.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Server-side fallback: if a safety classifier declines a request, the API
# re-runs it on Anthropic's recommended fallback model instead of refusing.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Models that reject output_config.effort (a 400, which would otherwise be
# reported as "LLM unavailable" and silently fall back to the rule agents).
_NO_EFFORT_MODELS = ("claude-haiku-4-5",)


class LLMUnavailable(RuntimeError):
    pass


class LLMClient:
    def __init__(self) -> None:
        self._sdk = None

    @property
    def available(self) -> bool:
        return settings.llm_enabled

    @property
    def provider(self) -> str:
        return settings.llm_provider.lower()

    @property
    def tool_calling_available(self) -> bool:
        return self.available and self.provider in ("anthropic", "openai")

    @property
    def model(self) -> str:
        return settings.active_llm_model

    def _sdk_client(self):
        if self._sdk is None:
            import anthropic  # only needed once a key is configured

            self._sdk = anthropic.Anthropic(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url or None,
                timeout=settings.llm_timeout_seconds,
                max_retries=1,
            )
        return self._sdk

    def create_message(self, *, system: str, messages: list, tools: list | None = None,
                       effort: str = "medium", max_tokens: int = 16000,
                       timeout: float | None = None, model: str | None = None,
                       fallbacks: bool | None = None):
        """One tool-capable Messages API call. Raises LLMUnavailable on any failure.

        `model` and `fallbacks` default to the configured values; the
        evaluation harness overrides them per run.
        """
        if not self.tool_calling_available:
            raise LLMUnavailable("LLM tool calling is not configured")
        if self.provider == "openai":
            from app.services.llm_providers import openai_client  # avoids an import cycle

            return openai_client.create_message(
                system=system, messages=messages, tools=tools, effort=effort,
                max_tokens=max_tokens, timeout=timeout, model=model or self.model)
        import anthropic

        model = model or settings.llm_model
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if not model.startswith(_NO_EFFORT_MODELS):
            kwargs["output_config"] = {"effort": effort}
        if tools:
            kwargs["tools"] = tools
        if settings.llm_fallbacks if fallbacks is None else fallbacks:
            kwargs["betas"] = [_FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        client = self._sdk_client()
        if timeout is not None:
            client = client.with_options(timeout=max(timeout, 5.0))
        try:
            response = client.beta.messages.create(**kwargs)
        except anthropic.APIError as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
        if response.stop_reason == "refusal":
            raise LLMUnavailable("Model declined the request")
        return response

    def complete(self, *, system: str, prompt: str, max_tokens: int = 1200) -> str:
        if not self.available:
            raise LLMUnavailable("No LLM API key configured")
        if self.provider == "openai":
            # Same Responses API path as the agents (gpt-5.5 needs it for reasoning).
            response = self.create_message(
                system=system, messages=[{"role": "user", "content": prompt}],
                effort="low", max_tokens=max(max_tokens, 1024))
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if not text:
                raise LLMUnavailable("Model returned no text")
            return text
        return self._anthropic(system, prompt, max_tokens)

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


llm_client = LLMClient()
