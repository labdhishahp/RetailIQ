"""Agent primitives: findings, execution traces, and the two ways an agent runs.

Every specialist has a fixed scope (its toolset) but no fixed script. It runs
in one of two modes, and the trace records which:

* llm   — the model picks tools and arguments, reads each result, and decides
          whether to dig further or conclude (runtime.run_tool_loop).
* rules — a policy generator does the same by rule: it yields a tool call,
          receives the result, and chooses its next call from what came back.

Both go through the same tool gate, so the trace and the data used for the
numeric parts of the answer are identical in shape.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generator

from sqlalchemy.orm import Session

from app.agents.runtime import Budget, run_tool_loop, to_tool_content
from app.agents.tools import TOOL_SPECS, ToolError, call_tool
from app.services.llm import LLMUnavailable

logger = logging.getLogger(__name__)

SEVERITIES = ("info", "warning", "critical")


@dataclass
class Finding:
    """One evidenced observation produced by a specialist."""

    statement: str
    severity: str = "info"        # info | warning | critical
    metric: float | None = None
    entity: str | None = None
    # True: every number in the statement appears in this agent's tool output.
    # False: at least one does not (derived or invented). None: no numbers.
    verified: bool | None = None

    def as_dict(self) -> dict:
        return {"statement": self.statement, "severity": self.severity,
                "metric": self.metric, "entity": self.entity, "verified": self.verified}


@dataclass
class ToolCall:
    tool: str
    args: dict = field(default_factory=dict)


def call(tool: str, **args) -> ToolCall:
    return ToolCall(tool, args)


@dataclass
class Context:
    question: str
    focus_term: str = ""
    objective: str = ""
    anchor: datetime | None = None


# Rule policies are generators: yield a ToolCall, receive its result, return findings.
Policy = Generator[ToolCall, object, list[Finding]]

# Tool output -> the AgentResult.data key the synthesis reads it from.
_DATA_KEYS = {
    "sales_summary": "summary", "product_sales_trend": "products",
    "category_performance": "categories", "product_drilldown": "drilldowns",
    "inventory_status": "inventory", "pricing_position": "pricing",
    "campaign_status": "campaigns", "store_performance": "stores",
    "search_knowledge_base": "citations",
}
_ROW_ID = ("sku", "code", "chunk_id", "store", "category")


@dataclass
class AgentResult:
    agent: str
    task: str
    objective: str = ""
    round: int = 1
    mode: str = "rules"                       # llm | rules
    findings: list[Finding] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)   # leads for the investigator
    data: dict = field(default_factory=dict)
    summary: str = ""
    follow_up: str = ""
    fallback: str | None = None               # why an llm run fell back to rules
    llm_turns: int = 0
    tokens: int = 0
    duration_ms: int = 0
    _observations: list = field(default_factory=list, repr=False)

    @property
    def severity(self) -> str:
        if any(f.severity == "critical" for f in self.findings):
            return "critical"
        if any(f.severity == "warning" for f in self.findings):
            return "warning"
        return "info"

    def signal(self, kind: str, **detail) -> None:
        self.signals.append({"kind": kind, "from": self.agent, **detail})

    def record(self, tool: str, value) -> None:
        self._observations.append(value)
        key = _DATA_KEYS.get(tool)
        if tool == "customer_health":
            self.data.update(value)
        elif tool == "sales_summary":
            self.data.setdefault("summary", value)
        elif tool == "product_drilldown":
            self.data.setdefault("drilldowns", []).append(value)
        elif key and isinstance(value, list):
            rows = self.data.setdefault(key, [])
            seen = {_row_key(r) for r in rows}
            rows.extend(r for r in value if _row_key(r) not in seen)

    def as_dict(self) -> dict:
        return {
            "agent": self.agent, "task": self.task, "objective": self.objective,
            "severity": self.severity, "mode": self.mode,
            "findings": [f.as_dict() for f in self.findings],
            "tools_called": self.tools_called, "steps": self.steps,
            "summary": self.summary, "follow_up": self.follow_up,
            "duration_ms": self.duration_ms,
        }


def _row_key(row) -> object:
    if isinstance(row, dict):
        for k in _ROW_ID:
            if k in row:
                return (k, row[k])
    return id(row)


# --------------------------------------------------------------------------
# Grounding check
# --------------------------------------------------------------------------

_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
# Thresholds and windows the agents are told about; quoting them is not a claim.
_KNOWN_CONSTANTS = {2, 5, 7, 10, 14, 21, 30, 45, 60, 90, 180, 365, 2.5, 1.5}


def _numbers(value, out: list[float]) -> list[float]:
    if isinstance(value, bool):
        return out
    if isinstance(value, (int, float)):
        out.append(float(value))
    elif isinstance(value, str):
        # Document excerpts and labels carry figures too (policy thresholds).
        for raw in _NUMBER.findall(value):
            try:
                out.append(float(raw.replace(",", "")))
            except ValueError:
                pass
    elif isinstance(value, dict):
        for v in value.values():
            _numbers(v, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _numbers(v, out)
    return out


def verify_statement(statement: str, observations: list) -> bool | None:
    """Does every number in `statement` appear (to display rounding) in the data?"""
    claimed = []
    for raw in _NUMBER.findall(statement):
        try:
            claimed.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    claimed = [c for c in claimed if c not in _KNOWN_CONSTANTS]
    if not claimed:
        return None
    pool = _numbers(observations, [])
    for c in claimed:
        tolerance = max(0.051, abs(c) * 0.006)
        if not any(abs(abs(p) - abs(c)) <= tolerance for p in pool):
            return False
    return True


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------

_FINISH = "submit_findings"
_FINISH_SPEC = {
    "name": _FINISH,
    "description": "Record your findings and end your investigation. Call exactly once, last.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "description": "Evidenced observations, most important first (at most 6).",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string",
                                      "description": "One sentence quoting figures exactly as the tools returned them."},
                        "severity": {"type": "string", "enum": list(SEVERITIES)},
                        "entity": {"type": "string",
                                   "description": "SKU, campaign code or store name the finding is about; empty if none."},
                    },
                    "required": ["statement", "severity", "entity"],
                    "additionalProperties": False,
                },
            },
            "summary": {"type": "string", "description": "Two sentences: what you established and how."},
            "follow_up": {"type": "string",
                          "description": "What another specialist should check next, or empty if nothing."},
        },
        "required": ["findings", "summary", "follow_up"],
        "additionalProperties": False,
    },
    "strict": True,
}


class Agent:
    """A specialist with a fixed scope and toolset, and no fixed script."""

    name: str = "agent"
    label: str = "Agent"
    task: str = ""
    icon: str = "Sparkles"
    tools: tuple[str, ...] = ()
    mission: str = ""          # domain guidance for the model

    def policy(self, ctx: Context, r: AgentResult) -> Policy:  # pragma: no cover
        raise NotImplementedError
        yield

    # -- shared tool gate --------------------------------------------------

    def _execute(self, db: Session, r: AgentResult, tool: str, args: dict):
        """Run one tool on behalf of this agent and trace it. Raises ToolError."""
        if tool not in self.tools:
            raise ToolError(f"{tool} is not available to the {self.label}")
        started = time.perf_counter()
        try:
            value = call_tool(db, tool, **args)
        except ToolError as exc:
            r.steps.append({"tool": tool, "args": args, "ok": False, "error": str(exc),
                            "ms": int((time.perf_counter() - started) * 1000)})
            raise
        r.tools_called.append(tool)
        r.record(tool, value)
        r.steps.append({"tool": tool, "args": args, "ok": True, "result": _summarise(tool, value),
                        "ms": int((time.perf_counter() - started) * 1000)})
        return value

    # -- entry point ---------------------------------------------------------

    def run(self, db: Session, ctx: Context, *, round: int = 1, llm=None,
            budget: Budget | None = None, effort: str = "low") -> AgentResult:
        started = time.perf_counter()
        r = AgentResult(agent=self.name, task=self.task, objective=ctx.objective, round=round)
        if llm is not None and budget is not None and budget.remaining() > 8:
            try:
                self._run_llm(db, ctx, r, llm, budget, effort)
            except LLMUnavailable as exc:
                logger.warning("%s fell back to rules: %s", self.name, exc)
                r = self._restart(r, f"llm_error: {exc}"[:200])
        if r.mode != "llm":
            self._run_rules(db, ctx, r)
        r.duration_ms = int((time.perf_counter() - started) * 1000)
        return r

    def _restart(self, r: AgentResult, reason: str) -> AgentResult:
        fresh = AgentResult(agent=r.agent, task=r.task, objective=r.objective, round=r.round,
                            fallback=reason, llm_turns=r.llm_turns, tokens=r.tokens)
        return fresh

    def _run_rules(self, db: Session, ctx: Context, r: AgentResult) -> None:
        r.mode = "rules"
        gen = self.policy(ctx, r)
        try:
            request = next(gen)
            while True:
                request = gen.send(self._execute(db, r, request.tool, request.args))
        except StopIteration as stop:
            findings = stop.value or []
        for f in findings:
            f.verified = verify_statement(f.statement, r._observations)
        r.findings = findings

    def _run_llm(self, db: Session, ctx: Context, r: AgentResult, llm, budget: Budget,
                 effort: str) -> None:
        r.mode = "llm"

        def execute(batch):
            out = []
            for _id, tool, args in batch:
                try:
                    out.append((to_tool_content(self._execute(db, r, tool, args)), False))
                except ToolError as exc:
                    out.append((str(exc), True))
            return out

        outcome = run_tool_loop(
            llm=llm, system=self._system_prompt(), prompt=self._prompt(ctx),
            tools=[TOOL_SPECS[t] for t in self.tools] + [_FINISH_SPEC],
            finish_tool=_FINISH, execute=execute,
            budget=Budget(deadline=budget.deadline, max_turns=budget.max_turns), effort=effort)
        r.llm_turns = outcome.turns
        r.tokens = outcome.input_tokens + outcome.output_tokens

        if outcome.final is None:
            # The model never concluded. Rather than report half an
            # investigation, rerun this agent on its rule policy; `fallback`
            # records why, and the trace shows the rule run.
            fresh = self._restart(r, f"llm_{outcome.stopped}")
            r.__dict__.update(fresh.__dict__)
            return

        r.summary = str(outcome.final.get("summary", ""))[:600]
        r.follow_up = str(outcome.final.get("follow_up", ""))[:300]
        for item in (outcome.final.get("findings") or [])[:6]:
            statement = str(item.get("statement", "")).strip()
            if not statement:
                continue
            severity = item.get("severity") if item.get("severity") in SEVERITIES else "info"
            r.findings.append(Finding(
                statement, severity, entity=(item.get("entity") or None),
                verified=verify_statement(statement, r._observations)))
        if not r.findings:
            r.findings.append(Finding("No material finding in this area.", "info"))

    def _system_prompt(self) -> str:
        return (
            f"You are the {self.label} in RetailIQ, a retail decision-intelligence copilot. "
            f"{self.mission}\n\n"
            "You investigate with tools that query the live operational database. Start with the "
            "broad tool that fits your objective, read what comes back, and then decide: drill "
            "into the specific product, store or campaign that explains the question, check a "
            "competing explanation, or stop. Do not repeat a call you have already made. Stop as "
            "soon as the evidence answers your objective; two to four tool calls is typical.\n\n"
            "Findings must be grounded: quote figures exactly as the tools returned them and "
            "never estimate a number a tool did not give you. Finish by calling submit_findings "
            "once."
        )

    def _prompt(self, ctx: Context) -> str:
        parts = [f"Business question: {ctx.question}"]
        if ctx.objective:
            parts.append(f"Your objective from the lead investigator: {ctx.objective}")
        if ctx.focus_term:
            parts.append(f"Focus: {ctx.focus_term} (pass it as name_contains where relevant).")
        if ctx.anchor:
            parts.append(f"Data is current to {ctx.anchor.date().isoformat()}.")
        return "\n".join(parts)


def _summarise(tool: str, value) -> str:
    """One line for the trace: what came back, not the whole payload."""
    if isinstance(value, list):
        if not value:
            return "no rows"
        first = value[0]
        label = first.get("name") or first.get("title") or first.get("store") or first.get("category")
        return f"{len(value)} rows" + (f"; first: {label}" if label else "")
    if isinstance(value, dict):
        if tool == "product_drilldown":
            if not value.get("found"):
                return f"SKU {value.get('sku')} not found"
            return (f"{value['name']}: units {value['units_change_pct']:+.1f}% over 4 weeks, "
                    f"price {value['price_change_pct']:+.1f}%, {value['on_hand_total']} on hand")
        if tool == "sales_summary":
            return f"revenue {value['revenue']:,.0f} ({value['revenue_change_pct']:+.1f}%)"
        if tool == "customer_health":
            return f"{value['at_risk_count']} at-risk customers, {value['at_risk_spend']:,.0f} spend"
        return f"{len(value)} fields"
    return "ok"
