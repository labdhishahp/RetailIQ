"""The model-driven tool loop shared by the lead investigator and specialists.

One loop: send the conversation, execute every tool the model asked for, return
all results in a single message, repeat. It ends when the model calls its
finishing tool, stops asking for tools, or runs out of turns or time. On the
last affordable turn the model is told to finish, so a budget never cuts an
agent off without a conclusion.
"""

import json
import time
from dataclasses import dataclass
from typing import Callable

from app.services.llm import LLMUnavailable

# (tool_use_id, name, input) -> (content, is_error)
BatchExecutor = Callable[[list[tuple[str, str, dict]]], list[tuple[str, bool]]]

_FINALIZE = ("Budget for this investigation is nearly spent. Do not call any more data tools: "
             "call {finish} now with what you have established.")
_NUDGE = "You have not called {finish}. Call it now to record your conclusion."


@dataclass
class LoopOutcome:
    final: dict | None              # the finishing tool's input, if it was called
    text: str = ""                  # any prose the model wrote
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    stopped: str = "finished"       # finished | no_conclusion | budget


@dataclass
class Budget:
    deadline: float                 # time.monotonic() value
    max_turns: int

    def remaining(self) -> float:
        return self.deadline - time.monotonic()


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    turns: int = 0


def to_tool_content(value) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


def run_tool_loop(*, llm, system: str, prompt: str, tools: list[dict], finish_tool: str,
                  execute: BatchExecutor, budget: Budget, effort: str) -> LoopOutcome:
    """Drive one agent until it concludes. Raises LLMUnavailable on API failure."""
    messages: list[dict] = []
    pending: str | list = prompt
    usage = _Usage()
    nudged = False
    text = ""

    for turn in range(budget.max_turns):
        last_turn = turn == budget.max_turns - 1 or budget.remaining() < 8
        if last_turn and turn > 0 and isinstance(pending, list):
            pending.append({"type": "text", "text": _FINALIZE.format(finish=finish_tool)})
        messages.append({"role": "user", "content": pending})

        response = llm.create_message(system=system, messages=messages, tools=tools,
                                      effort=effort, timeout=budget.remaining())
        usage.turns += 1
        if getattr(response, "usage", None) is not None:
            usage.input_tokens += response.usage.input_tokens or 0
            usage.output_tokens += response.usage.output_tokens or 0
        messages.append({"role": "assistant", "content": response.content})

        text = "".join(b.text for b in response.content if b.type == "text").strip() or text
        uses = [b for b in response.content if b.type == "tool_use"]

        def outcome(final, stopped):
            return LoopOutcome(final=final, text=text, turns=usage.turns,
                               input_tokens=usage.input_tokens,
                               output_tokens=usage.output_tokens, stopped=stopped)

        if response.stop_reason == "max_tokens" and not uses:
            return outcome(None, "no_conclusion")

        if not uses:
            if nudged or last_turn:
                return outcome(None, "no_conclusion")
            nudged = True
            pending = [{"type": "text", "text": _NUDGE.format(finish=finish_tool)}]
            continue

        finish = next((u for u in uses if u.name == finish_tool), None)
        if finish is not None:
            return outcome(dict(finish.input or {}), "finished")
        if last_turn:
            return outcome(None, "budget")

        results = execute([(u.id, u.name, dict(u.input or {})) for u in uses])
        pending = [
            {"type": "tool_result", "tool_use_id": u.id, "content": content, "is_error": is_error}
            for u, (content, is_error) in zip(uses, results)
        ]
        if budget.remaining() < 3:
            return outcome(None, "budget")

    return LoopOutcome(final=None, text=text, turns=usage.turns,
                       input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                       stopped="budget")


__all__ = ["Budget", "LoopOutcome", "LLMUnavailable", "run_tool_loop", "to_tool_content"]
