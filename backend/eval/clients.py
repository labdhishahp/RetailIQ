"""LLM clients for evaluation runs.

ModelClient pins every agent call in an investigation to one model, turns
server-side fallback off (a fallback would silently answer with a different
model and contaminate the comparison) and records usage per call. It goes
through the app's own LLMClient (Anthropic) or the provider adapters
(OpenAI, Gemini), so the request shape is exactly what the agents send.
"""

import threading
from collections import Counter

from app.services.llm import llm_client
from app.services.llm_providers import gemini_client, openai_client

# Supported tool-calling models, verified against the installed anthropic SDK's
# model list. USD per million tokens (input, output): Anthropic list prices as
# cached in the claude-api reference on 2026-09-25. Re-check
# https://platform.claude.com/docs/en/about-claude/pricing before publishing costs.
# OpenAI and Gemini: no verified price in the project yet, so cost is reported
# as unknown (None) rather than guessed. Fill in from the providers' official
# pricing pages before publishing costs.
PRICING: dict[str, tuple[float, float] | None] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "gpt-5.5": None,
    "gemini-3.5-flash": None,
}
DEFAULT_MODELS = list(PRICING)


def provider_client(model: str):
    """The client that serves a model id; it never substitutes another model."""
    if model.startswith("gpt-"):
        return openai_client
    if model.startswith("gemini-"):
        return gemini_client
    return llm_client


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    price = PRICING.get(model)
    if price is None:
        return None
    return round(input_tokens / 1e6 * price[0] + output_tokens / 1e6 * price[1], 6)


class RulesOnly:
    """The free baseline: no model, so every agent runs its rule policy."""

    tool_calling_available = False
    model = "rules"

    def reset(self) -> None:
        pass

    def usage(self) -> dict:
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
                "served_models": {}, "errors": 0}


class ModelClient:
    def __init__(self, model: str, inner=None):
        self.model = model
        self._inner = inner if inner is not None else provider_client(model)
        self._lock = threading.Lock()   # parallel delegations call from threads
        self.reset()

    @property
    def tool_calling_available(self) -> bool:
        return self._inner.tool_calling_available

    def reset(self) -> None:
        with self._lock:
            self._usage = Counter()
            self._served = Counter()

    def create_message(self, **kwargs):
        try:
            response = self._inner.create_message(**kwargs, model=self.model, fallbacks=False)
        except Exception:
            with self._lock:
                self._usage["errors"] += 1
            raise
        usage = getattr(response, "usage", None)
        with self._lock:
            self._usage["calls"] += 1
            for field in ("input_tokens", "output_tokens",
                          "cache_read_input_tokens", "cache_creation_input_tokens"):
                self._usage[field] += int(getattr(usage, field, 0) or 0)
            self._served[getattr(response, "model", None) or "unknown"] += 1
        return response

    def usage(self) -> dict:
        with self._lock:
            return {
                "calls": self._usage["calls"],
                "input_tokens": self._usage["input_tokens"],
                "output_tokens": self._usage["output_tokens"],
                "cache_read_input_tokens": self._usage["cache_read_input_tokens"],
                "cache_creation_input_tokens": self._usage["cache_creation_input_tokens"],
                "served_models": dict(self._served),
                "errors": self._usage["errors"],
            }
