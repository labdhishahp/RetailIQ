"""The lead investigator: delegates to specialists, reads what they find, and
decides whether to dig further before concluding.

With an Anthropic key the lead is a model in a tool loop. Its tools are
`delegate` (send a specialist with an objective and focus; several in one turn
run in parallel) and `submit_conclusion`. It sees each specialist's findings
and decides on follow-ups itself.

Without a key the lead runs by rule, and is still observation-driven: a first
round chosen from the question's intent, a second round chosen from the leads
(signals) the first round raised, then a knowledge search phrased from what
was found.

The synthesis output matches the structure the existing RecommendationCard
renders: root cause, evidence, confidence, business impact, risk level,
suggested action and next steps. The numeric fields (confidence, revenue
impact, inventory impact) are always computed from tool output, never by the
model.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.agents.base import AgentResult, Context, verify_statement
from app.agents.planner import build_plan
from app.agents.runtime import Budget, run_tool_loop, to_tool_content
from app.agents.specialists import SPECIALISTS
from app.core.config import settings
from app.models import AgentRun
from app.services.analytics_service import analytics_service
from app.services.llm import LLMUnavailable, llm_client

logger = logging.getLogger(__name__)


def _severity_rank(results: list[AgentResult]) -> str:
    if any(r.severity == "critical" for r in results):
        return "high"
    if any(r.severity == "warning" for r in results):
        return "medium"
    return "low"


def _confidence(results: list[AgentResult]) -> int:
    """Confidence rises with corroborating agents and evidence volume."""
    evidence = sum(len(r.findings) for r in results)
    agents = len([r for r in results if r.findings])
    score = 45 + min(agents, 6) * 5 + min(evidence, 12) * 2
    return max(35, min(score, 95))


def _revenue_at_risk(results: list[AgentResult]) -> float:
    total = 0.0
    for r in results:
        summary = r.data.get("summary")
        if summary and summary.get("revenue_change_pct", 0) < 0:
            total += abs(summary["revenue"] * summary["revenue_change_pct"] / 100)
        for item in r.data.get("inventory", []):
            if item.get("days_cover") is not None and item["days_cover"] < 21:
                total += item.get("stock_value", 0) * 0.15
    return round(total, 2)


def _fallback_synthesis(question: str, results: list[AgentResult], plan: dict) -> dict:
    """Compose a grounded narrative from the specialists' findings.

    Findings are ranked by the agent's relevance to the question first (the
    planner returns agents in priority order) and by severity second, so the
    headline answers what was actually asked rather than always surfacing the
    single worst number anywhere in the business.
    """
    priority = {name: i for i, name in enumerate(plan.get("agents", []))}
    sev_rank = {"critical": 0, "warning": 1, "info": 2}

    scored = [
        (priority.get(r.agent, 99), sev_rank.get(f.severity, 3), r.agent, f)
        for r in results for f in r.findings
    ]
    scored.sort(key=lambda t: (t[0], t[1]))

    primary_agent = plan.get("agents", ["sales"])[0]
    material = [t for t in scored if t[1] <= 1]          # critical or warning
    primary_material = [t for t in material if t[2] == primary_agent]
    drivers = [t[3] for t in (primary_material or material)][:6]

    if drivers:
        root = "Primary driver: " + drivers[0].statement
        others = sorted({t[2] for t in material if t[2] != primary_agent})
        if others:
            root += (" Supporting signals were found in "
                     + ", ".join(others) + ".")
    else:
        root = ("No material risk was detected for this question. The metrics examined are "
                "within normal ranges for the period analysed.")

    # Actions are derived from the underlying rows, not from the prose.
    steps: list[str] = []
    for r in results:
        for item in r.data.get("inventory", []):
            if item.get("days_cover") is not None and item["days_cover"] < 21:
                steps.append(
                    f"Raise a purchase order for {item['name']} "
                    f"({item['reorder_quantity']} units) — {item['days_cover']} days of cover left.")
            elif item.get("below_reorder"):
                steps.append(
                    f"{item['name']} is below its reorder level "
                    f"({item['on_hand']} on hand vs {item['reorder_level']}) — replenish.")
            elif item.get("daily_velocity") == 0 and item.get("on_hand", 0) > 0:
                steps.append(
                    f"Review {item['name']}: {item['on_hand']} units with no recent sales "
                    f"({item['stock_value']:,.0f} tied up).")
        for p in r.data.get("pricing", []):
            if p["discount_vs_list_pct"] > 5 and p["units_90d"] > 0:
                steps.append(
                    f"Review discounting on {p['name']}: selling "
                    f"{p['discount_vs_list_pct']:.1f}% below list.")
        for c in r.data.get("campaigns", []):
            if c["status"] == "active" and c["roi"] < 2.5:
                steps.append(f"Reallocate budget from '{c['name']}' (ROI {c['roi']:.1f}x).")
        for cust in r.data.get("at_risk", [])[:2]:
            steps.append(
                f"Run a win-back offer for {cust['name']} "
                f"(last order {cust['last_order'] or 'unknown'}, {cust['spend']:,.0f} lifetime).")
        for st in r.data.get("stores", []):
            if st.get("growth", 0) < -5:
                steps.append(
                    f"Investigate {st['store']}: revenue contracting {st['growth']:+.1f}%.")

    # de-duplicate while preserving order, and lead with the primary agent's actions
    seen, ordered = set(), []
    for step in steps:
        if step not in seen:
            seen.add(step)
            ordered.append(step)
    if not ordered:
        ordered = ["No corrective action indicated: the areas examined are within tolerance."]

    action = ordered[0] if drivers else "Maintain current plan and re-evaluate next cycle."
    impact = _revenue_at_risk(results)
    return {
        "rootCause": root,
        "evidence": [t[3].statement for t in scored][:10],
        "businessImpact": (f"Estimated {impact:,.0f} of revenue exposure if unaddressed."
                           if impact else "No material revenue exposure identified."),
        "riskLevel": _severity_rank(results),
        "suggestedCampaign": action,
        "nextSteps": ordered[:5],
        "synthesis": "rules",
    }


# --------------------------------------------------------------------------
# Investigation state shared by both leads
# --------------------------------------------------------------------------

class _Investigation:
    def __init__(self, db: Session, question: str, focus: str):
        self.db = db
        self.question = question
        self.focus = focus
        self.anchor = analytics_service._now(db)
        self.results: list[AgentResult] = []
        self.decisions: list[dict] = []
        self.ran: set[tuple[str, str]] = set()
        self.round = 0
        self.delegations = 0
        self.lead_turns = 0
        self.lead_tokens = 0
        self.fallback: str | None = None

    def context(self, objective: str, focus: str) -> Context:
        return Context(question=self.question, focus_term=focus, objective=objective,
                       anchor=self.anchor)

    def decide(self, *, agent: str, objective: str, focus: str, reason: str, by: str) -> None:
        self.decisions.append({"round": self.round, "agent": agent, "objective": objective,
                               "focus": focus, "reason": reason, "by": by})
        self.ran.add((agent, focus.lower()))

    def run_one(self, db: Session, agent: str, objective: str, focus: str, *,
                llm=None, budget: Budget | None = None) -> AgentResult:
        agent_cls = SPECIALISTS[agent]
        try:
            return agent_cls().run(db, self.context(objective, focus), round=self.round,
                                   llm=llm, budget=budget, effort=settings.llm_agent_effort)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent %s failed", agent)
            failed = AgentResult(agent=agent, task=agent_cls.task, objective=objective,
                                 round=self.round)
            failed.data = {"error": type(exc).__name__}
            return failed


# --------------------------------------------------------------------------
# Rule-driven lead
# --------------------------------------------------------------------------

# A lead raised by one specialist -> who should follow it up, and to what end.
_FOLLOW_UPS: dict[str, list[tuple[str, str]]] = {
    "product_decline": [("inventory", "Check whether stock availability explains the fall in {name}"),
                        ("pricing", "Check whether price movement explains the fall in {name}")],
    "stock_constrained": [("inventory", "Assess the stock position and reorder need for {name}")],
    "price_increase": [("pricing", "Assess pricing and realised margin on {name}")],
    "discount_ineffective": [("pricing", "Assess whether discounting on {name} is worth its margin")],
    "dead_stock": [("pricing", "Assess whether a markdown could clear {name}")],
    "stock_risk": [("sales", "Confirm the demand trend behind the stock risk on {name}")],
    "store_concentration": [("store", "Compare {store} with the other locations")],
    "campaign_underperform": [("customer", "Check whether lapsed customers are a better use of the spend")],
}
_MAX_FOLLOW_UPS = 3

_KNOWLEDGE_TERMS = {
    "stock_risk": "reorder policy days of cover", "stock_constrained": "replenishment stockout",
    "dead_stock": "dead stock markdown clearance", "price_increase": "pricing policy",
    "discount_ineffective": "discount markdown policy",
    "campaign_underperform": "campaign ROI budget reallocation",
    "churn_exposure": "customer win-back retention", "store_concentration": "store operations",
    "store_decline": "store performance", "product_decline": "sales decline",
    "demand_decline": "demand forecast", "category_decline": "category performance",
}


# Agents whose tools take no product filter: a second run can only repeat the first.
_UNFOCUSED = {"campaign", "customer", "store", "knowledge"}


def _already_covered(inv: _Investigation, agent: str, sku: str | None) -> bool:
    """Has an earlier run of `agent` already examined this product?"""
    runs = [r for r in inv.results if r.agent == agent]
    if not runs:
        return False
    if agent in _UNFOCUSED or not sku:
        return True
    for r in runs:
        for value in r.data.values():
            if isinstance(value, list) and any(isinstance(row, dict) and row.get("sku") == sku
                                               for row in value):
                return True
    return False


def _follow_ups(inv: _Investigation) -> list[dict]:
    planned, keys = [], set(inv.ran)
    for r in inv.results:
        for s in r.signals:
            for agent, template in _FOLLOW_UPS.get(s["kind"], []):
                focus = s.get("name", "") if agent not in _UNFOCUSED else ""
                key = (agent, focus.lower())
                if key in keys or _already_covered(inv, agent, s.get("sku")):
                    continue
                keys.add(key)
                subject = s.get("name") or s.get("store") or s.get("code") or ""
                planned.append({
                    "agent": agent, "focus": focus,
                    "objective": template.format(name=s.get("name", ""), store=s.get("store", "")),
                    "reason": f"{SPECIALISTS[r.agent].label} reported {s['kind'].replace('_', ' ')}"
                              + (f" for {subject}" if subject else ""),
                })
    return planned[:_MAX_FOLLOW_UPS]


def _knowledge_query(inv: _Investigation) -> str:
    terms: list[str] = []
    for r in inv.results:
        for s in r.signals:
            term = _KNOWLEDGE_TERMS.get(s["kind"])
            if term and term not in terms:
                terms.append(term)
    return " ".join([inv.question] + terms[:3])


def _lead_by_rules(inv: _Investigation, plan: dict) -> None:
    inv.round = 1
    for agent in [a for a in plan["agents"] if a != "knowledge"]:
        inv.decide(agent=agent, objective=SPECIALISTS[agent].task, focus=inv.focus,
                   reason=plan["reason"], by="rules")
        inv.results.append(inv.run_one(inv.db, agent, SPECIALISTS[agent].task, inv.focus))

    follow = _follow_ups(inv)
    if follow:
        inv.round += 1
        for f in follow:
            inv.decide(agent=f["agent"], objective=f["objective"], focus=f["focus"],
                       reason=f["reason"], by="rules")
            inv.results.append(inv.run_one(inv.db, f["agent"], f["objective"], f["focus"]))

    if "knowledge" in plan["agents"]:
        inv.round += 1
        query = _knowledge_query(inv)
        inv.decide(agent="knowledge", objective=query, focus="",
                   reason="find the policy that governs what the specialists found", by="rules")
        inv.results.append(inv.run_one(inv.db, "knowledge", query, ""))


# --------------------------------------------------------------------------
# Model-driven lead
# --------------------------------------------------------------------------

_CONCLUDE = "submit_conclusion"

_LEAD_TOOLS = [
    {
        "name": "delegate",
        "description": ("Send a specialist agent to investigate. It queries the live database "
                        "with its own tools and returns evidenced findings. Several delegate "
                        "calls in one turn run in parallel."),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": list(SPECIALISTS)},
                "objective": {"type": "string",
                              "description": "What this specialist must establish, specifically."},
                "focus": {"type": "string",
                          "description": "Product name to narrow to, or empty string for none."},
            },
            "required": ["agent", "objective", "focus"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": _CONCLUDE,
        "description": "Record the investigation's conclusion. Call exactly once, last.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rootCause": {"type": "string",
                              "description": "The cause that answers the question, in two or three sentences."},
                "evidence": {"type": "array", "items": {"type": "string"},
                             "description": "Specialist findings that support the root cause, verbatim."},
                "businessImpact": {"type": "string"},
                "riskLevel": {"type": "string", "enum": ["low", "medium", "high"]},
                "suggestedCampaign": {"type": "string",
                                      "description": "The single most important action."},
                "nextSteps": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["rootCause", "evidence", "businessImpact", "riskLevel",
                         "suggestedCampaign", "nextSteps"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _lead_system_prompt() -> str:
    roster = "\n".join(
        f"- {name} ({cls.label}): {cls.mission} Tools: {', '.join(cls.tools)}."
        for name, cls in SPECIALISTS.items())
    return (
        "You are the lead investigator in RetailIQ, a retail decision-intelligence copilot. "
        "You answer a business question by directing specialist agents, each of which queries "
        "the live operational database with its own tools.\n\n"
        f"Specialists:\n{roster}\n\n"
        "Work like an analyst. Delegate first to the specialists whose domain bears on the "
        "question, each with a specific objective; independent delegations belong in the same "
        "turn so they run in parallel. Read what comes back. If the findings leave the cause "
        "unexplained, conflict with each other, or point at a specific product, store or "
        "campaign, delegate a narrower follow-up with a focus. Consult the knowledge agent for "
        "the policy that governs the issue before concluding. Stop when the evidence answers "
        f"the question; you have at most {settings.lead_max_delegations} delegations.\n\n"
        "Your conclusion must rest on the specialists' findings. Quote figures exactly as they "
        "reported them and never introduce a number they did not give you. A finding marked "
        "verified: false contains a figure that is not in the tool output; do not rely on it. "
        "Finish by calling submit_conclusion."
    )


def _report(r: AgentResult) -> dict:
    """What the lead sees of a specialist's run."""
    out = {
        "agent": r.agent, "mode": r.mode, "summary": r.summary,
        "findings": [{"statement": f.statement, "severity": f.severity,
                      "entity": f.entity, "verified": f.verified} for f in r.findings],
        "follow_up": r.follow_up, "tools_called": r.tools_called,
    }
    if r.data.get("error"):
        out["error"] = f"agent failed: {r.data['error']}"
    return out


def _lead_by_model(inv: _Investigation, llm, deadline: float) -> dict | None:
    """Run the model as lead. Returns its conclusion, or None if it gave none."""
    agent_budget = Budget(deadline=deadline - 8, max_turns=settings.agent_max_turns)

    def run_delegation(job: dict) -> AgentResult:
        if job["shared"]:
            return inv.run_one(inv.db, job["agent"], job["objective"], job["focus"],
                               llm=llm, budget=agent_budget)
        # A Session is not thread-safe: parallel specialists each get their own.
        own = Session(bind=inv.db.get_bind())
        try:
            return inv.run_one(own, job["agent"], job["objective"], job["focus"],
                               llm=llm, budget=agent_budget)
        finally:
            own.close()

    def execute(batch):
        out: list[tuple[str, bool] | None] = [None] * len(batch)
        jobs = []
        for i, (_id, name, args) in enumerate(batch):
            agent = args.get("agent")
            if name != "delegate" or agent not in SPECIALISTS:
                out[i] = (f"Unknown tool or agent: {name} {agent}", True)
            elif inv.delegations >= settings.lead_max_delegations:
                out[i] = ("Delegation budget exhausted. Conclude with what you have.", True)
            elif agent_budget.remaining() < 8:
                out[i] = ("No time left for another delegation. Conclude now.", True)
            else:
                inv.delegations += 1
                jobs.append({"i": i, "agent": agent, "objective": str(args.get("objective", "")),
                             "focus": str(args.get("focus", ""))})
        if jobs:
            inv.round += 1
            for job in jobs:
                job["shared"] = len(jobs) == 1
                inv.decide(agent=job["agent"], objective=job["objective"], focus=job["focus"],
                           reason="chosen by the lead investigator", by="llm")
            if len(jobs) == 1:
                results = [run_delegation(jobs[0])]
            else:
                with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                    results = list(pool.map(run_delegation, jobs))
            for job, r in zip(jobs, results):
                inv.results.append(r)
                out[job["i"]] = (to_tool_content(_report(r)), False)
        return out

    prompt = (f"Business question: {inv.question}\n"
              f"Data is current to {inv.anchor.date().isoformat()}.")
    if inv.focus:
        prompt += f"\nThe question appears to be about the product '{inv.focus}'."

    outcome = run_tool_loop(
        llm=llm, system=_lead_system_prompt(), prompt=prompt, tools=_LEAD_TOOLS,
        finish_tool=_CONCLUDE, execute=execute,
        budget=Budget(deadline=deadline, max_turns=settings.lead_max_turns),
        effort=settings.llm_lead_effort)
    inv.lead_turns = outcome.turns
    inv.lead_tokens = outcome.input_tokens + outcome.output_tokens
    if outcome.final is None:
        inv.fallback = f"lead_{outcome.stopped}"
    return outcome.final


_TEXT_KEYS = ("rootCause", "businessImpact", "suggestedCampaign")
_LIST_KEYS = ("evidence", "nextSteps")


def _valid_conclusion(final: dict | None) -> dict:
    """Keep only well-formed fields; anything missing falls back to rules."""
    if not isinstance(final, dict):
        return {}
    out = {}
    for key in _TEXT_KEYS:
        if isinstance(final.get(key), str) and final[key].strip():
            out[key] = final[key].strip()
    for key in _LIST_KEYS:
        items = [str(x).strip() for x in final.get(key) or [] if str(x).strip()]
        if items:
            out[key] = items[:10]
    if final.get("riskLevel") in ("low", "medium", "high"):
        out["riskLevel"] = final["riskLevel"]
    return out


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def investigate(db: Session, question: str, *, conversation_id: int | None = None,
                llm=None) -> dict:
    """Run an investigation for a question and return a result payload."""
    llm = llm_client if llm is None else llm
    started = time.perf_counter()
    deadline = time.monotonic() + settings.agent_deadline_seconds
    plan = build_plan(db, question)
    inv = _Investigation(db, question, plan["focus_term"])

    conclusion: dict = {}
    mode = "rules"
    if llm.tool_calling_available:
        mode = "llm"
        try:
            conclusion = _valid_conclusion(_lead_by_model(inv, llm, deadline))
        except LLMUnavailable as exc:
            logger.warning("Lead investigator unavailable (%s); continuing by rules.", exc)
            inv.fallback = f"lead_llm_error: {exc}"[:200]
        if not inv.results:
            mode = "rules"
            inv.decisions, inv.ran, inv.round = [], set(), 0
    if not inv.results:
        _lead_by_rules(inv, plan)

    results = inv.results
    order: list[str] = []
    for r in results:
        if r.agent not in order:
            order.append(r.agent)
    synthesis = _fallback_synthesis(question, results, {"agents": order})
    if conclusion:
        synthesis.update(conclusion)
        complete = all(k in conclusion for k in _TEXT_KEYS + _LIST_KEYS + ("riskLevel",))
        synthesis["synthesis"] = "llm" if complete else "llm_partial"

    observations = [o for r in results for o in r._observations]
    unverified = [s for s in [synthesis["rootCause"], *synthesis["evidence"]]
                  if verify_statement(s, observations) is False]

    citations = []
    for r in results:
        citations.extend(r.data.get("citations", []))

    seen_ids: dict[str, int] = {}
    agents = []
    for r in results:
        seen_ids[r.agent] = seen_ids.get(r.agent, 0) + 1
        cls = SPECIALISTS.get(r.agent)
        agents.append({
            "id": r.agent if seen_ids[r.agent] == 1 else f"{r.agent}-{seen_ids[r.agent]}",
            "agent": r.agent,
            "name": cls.label if cls else r.agent,
            "icon": cls.icon if cls else "Sparkles",
            "task": r.task, "objective": r.objective, "round": r.round, "mode": r.mode,
            "severity": r.severity, "duration": r.duration_ms,
            "findings": [f.as_dict() for f in r.findings],
            "toolsCalled": r.tools_called, "steps": r.steps,
            "fallback": r.fallback,
        })

    result = {
        **synthesis,
        "confidence": _confidence(results),
        "revenueImpact": -_revenue_at_risk(results),
        "priority": _severity_rank(results),
        "inventoryImpact": next(
            (f"{i['on_hand']} units of {i['name']} at {i['days_cover']} days cover"
             for r in results for i in r.data.get("inventory", [])
             if i.get("days_cover") is not None and i["days_cover"] < 21),
            "No immediate inventory risk identified."),
        "agents": agents,
        "citations": citations,
        "plan": {"agents": order, "focus_term": inv.focus, "intent": plan["intent"],
                 "planner": mode, "rounds": inv.round},
        "trace": {
            "mode": mode,
            "decisions": inv.decisions,
            "delegations": len(inv.decisions),
            "toolCalls": sum(len(r.steps) for r in results),
            "llmTurns": inv.lead_turns + sum(r.llm_turns for r in results),
            "tokens": inv.lead_tokens + sum(r.tokens for r in results),
            "unverifiedClaims": unverified,
            "fallback": inv.fallback,
        },
        "elapsedMs": int((time.perf_counter() - started) * 1000),
    }

    if conversation_id:
        for r in results:
            db.add(AgentRun(
                conversation_id=conversation_id, agent=r.agent, task=r.task,
                tools_called=r.tools_called,
                findings={"items": [f.as_dict() for f in r.findings], "steps": r.steps,
                          "objective": r.objective, "round": r.round, "mode": r.mode},
                duration_ms=r.duration_ms, tokens_used=r.tokens, status="complete",
            ))
    return result
