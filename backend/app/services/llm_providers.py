"""OpenAI and Gemini adapters for the agent runtime.

Each adapter implements the same create_message() contract as LLMClient, so
the lead, specialists and runtime loop run unchanged:

* in:  Anthropic-format system / messages / tools (tool_use and tool_result blocks)
* out: an object with stop_reason, content blocks (type "text" or "tool_use"
       with id/name/input), usage.input_tokens/output_tokens and model.

State the providers need between turns is carried inside the returned
content and replayed verbatim on the next call: OpenAI's output items
(including encrypted reasoning) and Gemini's model parts (including
thoughtSignature). The runtime ignores block types it does not know.

An adapter never switches model. Failures raise LLMUnavailable, which the
runtime already handles (the agent falls back to its rule policy and the
trace records it).
"""

import json
import logging
import time
import uuid
from types import SimpleNamespace

import httpx

from app.core.config import settings
from app.services.llm import LLMUnavailable

logger = logging.getLogger(__name__)

_RETRYABLE = {429, 500, 502, 503, 504}


def _post(url: str, *, headers: dict, body: dict, params: dict | None, timeout: float | None) -> dict:
    """POST with a short retry on rate-limit / overload responses."""
    timeout = max(timeout or settings.llm_timeout_seconds, 5.0)
    deadline = time.monotonic() + timeout
    for attempt in range(3):
        try:
            r = httpx.post(url, headers=headers, params=params, json=body,
                           timeout=max(deadline - time.monotonic(), 5.0))
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
        if r.status_code == 200:
            return r.json()
        if r.status_code in _RETRYABLE and attempt < 2 and deadline - time.monotonic() > 10:
            time.sleep(2 * (attempt + 1))
            continue
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except ValueError:
            detail = r.text
        raise LLMUnavailable(f"HTTP {r.status_code}: {str(detail)[:300]}")
    raise LLMUnavailable("retries exhausted")  # pragma: no cover


def _parse_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {"_invalid_arguments": raw}
    except ValueError:
        # Surfaces to the model as a tool error rather than being dropped.
        return {"_invalid_arguments": raw}


def _blocks(texts: list[str], calls: list[tuple[str, str, dict]], state) -> list:
    out = [state]
    out += [SimpleNamespace(type="text", text=t) for t in texts if t]
    out += [SimpleNamespace(type="tool_use", id=i, name=n, input=a) for i, n, a in calls]
    return out


# --------------------------------------------------------------------------
# OpenAI — Responses API
# --------------------------------------------------------------------------

class OpenAIResponsesClient:
    """gpt-5.5 rejects function tools with reasoning on Chat Completions, so this
    uses /v1/responses, statelessly (store=false) with encrypted reasoning."""

    url = "https://api.openai.com/v1/responses"

    @property
    def tool_calling_available(self) -> bool:
        return bool(settings.openai_api_key)

    def create_message(self, *, system: str, messages: list, tools: list | None = None,
                       effort: str = "medium", max_tokens: int = 16000,
                       timeout: float | None = None, model: str | None = None,
                       fallbacks: bool | None = None):
        if not self.tool_calling_available:
            raise LLMUnavailable("OPENAI_API_KEY is not configured")
        body = {
            "model": model or "gpt-5.5",
            "instructions": system,
            "input": self._input(messages),
            "reasoning": {"effort": effort},
            "max_output_tokens": max_tokens,
            "store": False,
            "include": ["reasoning.encrypted_content"],
        }
        if tools:
            body["tools"] = [{"type": "function", "name": t["name"], "description": t["description"],
                              "parameters": t["input_schema"], "strict": bool(t.get("strict"))}
                             for t in tools]
        data = _post(self.url, headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                     body=body, params=None, timeout=timeout)
        return self._response(data)

    @staticmethod
    def _input(messages: list) -> list:
        items: list = []
        for m in messages:
            content = m["content"]
            if m["role"] == "assistant":
                state = next((b for b in content if getattr(b, "type", None) == "openai_items"), None)
                if state is not None:
                    items.extend(state.items)       # reasoning + message + function_call, verbatim
                    continue
                for b in content:                  # history not produced by this adapter
                    if b.type == "text":
                        items.append({"role": "assistant", "content": b.text})
                    elif b.type == "tool_use":
                        items.append({"type": "function_call", "call_id": b.id, "name": b.name,
                                      "arguments": json.dumps(b.input)})
            elif isinstance(content, str):
                items.append({"role": "user", "content": content})
            else:
                for part in content:
                    if part.get("type") == "tool_result":
                        output = part["content"]
                        if part.get("is_error"):
                            output = f"ERROR: {output}"
                        items.append({"type": "function_call_output",
                                      "call_id": part["tool_use_id"], "output": output})
                    elif part.get("type") == "text":
                        items.append({"role": "user", "content": part["text"]})
        return items

    @staticmethod
    def _response(data: dict):
        output = data.get("output") or []
        texts, calls = [], []
        for item in output:
            if item.get("type") == "message":
                for c in item.get("content") or []:
                    if c.get("type") == "refusal":
                        raise LLMUnavailable("Model declined the request")
                    if c.get("type") == "output_text":
                        texts.append(c.get("text", ""))
            elif item.get("type") == "function_call":
                calls.append((item["call_id"], item["name"], _parse_args(item.get("arguments"))))
        if calls:
            stop = "tool_use"
        elif (data.get("status") == "incomplete"
              and (data.get("incomplete_details") or {}).get("reason") == "max_output_tokens"):
            stop = "max_tokens"
        else:
            stop = "end_turn"
        usage = data.get("usage") or {}
        return SimpleNamespace(
            model=data.get("model"), stop_reason=stop,
            content=_blocks(texts, calls, SimpleNamespace(type="openai_items", items=output)),
            usage=SimpleNamespace(input_tokens=usage.get("input_tokens", 0),
                                  output_tokens=usage.get("output_tokens", 0)))


# --------------------------------------------------------------------------
# Gemini — generateContent
# --------------------------------------------------------------------------

_BLOCKED = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


class GeminiClient:
    """Gemini 3 requires each functionCall part's thoughtSignature to be sent
    back on the next turn; the model's parts are therefore replayed verbatim."""

    base = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def tool_calling_available(self) -> bool:
        return bool(settings.gemini_api_key)

    def create_message(self, *, system: str, messages: list, tools: list | None = None,
                       effort: str = "medium", max_tokens: int = 16000,
                       timeout: float | None = None, model: str | None = None,
                       fallbacks: bool | None = None):
        if not self.tool_calling_available:
            raise LLMUnavailable("GEMINI_API_KEY is not configured")
        model = model or "gemini-3.5-flash"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self._contents(messages),
            # The runtime's effort (low for specialists, medium for the lead)
            # maps to Gemini's thinking level, as it maps to OpenAI's reasoning effort.
            "generationConfig": {"maxOutputTokens": max_tokens,
                                 "thinkingConfig": {"thinkingLevel": effort}},
        }
        if tools:
            # parametersJsonSchema takes standard JSON Schema (additionalProperties etc.).
            body["tools"] = [{"functionDeclarations": [
                {"name": t["name"], "description": t["description"],
                 "parametersJsonSchema": t["input_schema"]} for t in tools]}]
        data = _post(f"{self.base}/{model}:generateContent",
                     headers={"x-goog-api-key": settings.gemini_api_key},
                     body=body, params=None, timeout=timeout)
        return self._response(data, model)

    @staticmethod
    def _contents(messages: list) -> list:
        contents: list = []
        names: dict[str, str] = {}          # tool_use id -> function name
        for m in messages:
            content = m["content"]
            if m["role"] == "assistant":
                for b in content:
                    if getattr(b, "type", None) == "tool_use":
                        names[b.id] = b.name
                state = next((b for b in content if getattr(b, "type", None) == "gemini_parts"), None)
                if state is not None:
                    contents.append({"role": "model", "parts": state.parts})   # keeps thoughtSignature
                    continue
                parts = [{"text": b.text} for b in content if b.type == "text"]
                parts += [{"functionCall": {"id": b.id, "name": b.name, "args": b.input}}
                          for b in content if b.type == "tool_use"]
                contents.append({"role": "model", "parts": parts})
            elif isinstance(content, str):
                contents.append({"role": "user", "parts": [{"text": content}]})
            else:
                parts = []
                for part in content:
                    if part.get("type") == "tool_result":
                        key = "error" if part.get("is_error") else "result"
                        parts.append({"functionResponse": {
                            "id": part["tool_use_id"], "name": names.get(part["tool_use_id"], ""),
                            "response": {key: part["content"]}}})
                    elif part.get("type") == "text":
                        parts.append({"text": part["text"]})
                contents.append({"role": "user", "parts": parts})
        return contents

    @staticmethod
    def _response(data: dict, model: str):
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise LLMUnavailable(f"Gemini returned no candidates ({reason})")
        candidate = candidates[0]
        finish = candidate.get("finishReason", "")
        if finish in _BLOCKED:
            raise LLMUnavailable(f"Model declined the request ({finish})")
        parts = (candidate.get("content") or {}).get("parts") or []
        texts, calls = [], []
        for p in parts:
            if "functionCall" in p:
                fc = p["functionCall"]
                if not fc.get("id"):
                    fc["id"] = f"call_{uuid.uuid4().hex[:12]}"    # stored in the replayed part too
                calls.append((fc["id"], fc["name"], _parse_args(fc.get("args") or {})))
            elif "text" in p and not p.get("thought"):
                texts.append(p["text"])
        stop = "tool_use" if calls else ("max_tokens" if finish == "MAX_TOKENS" else "end_turn")
        usage = data.get("usageMetadata") or {}
        return SimpleNamespace(
            model=data.get("modelVersion") or model, stop_reason=stop,
            content=_blocks(texts, calls, SimpleNamespace(type="gemini_parts", parts=parts)),
            usage=SimpleNamespace(
                input_tokens=usage.get("promptTokenCount", 0),
                # Thinking tokens are billed as output.
                output_tokens=usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)))


openai_client = OpenAIResponsesClient()
gemini_client = GeminiClient()
