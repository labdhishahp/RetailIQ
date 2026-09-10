"""Runs the planned specialists and synthesises their findings.

The synthesis output matches the structure the existing RecommendationCard
renders: root cause, evidence, confidence, business impact, risk level,
suggested action and next steps.
"""

import logging
import time

from sqlalchemy.orm import Session

from app.agents.base import AgentResult
from app.agents.planner import build_plan
from app.agents.specialists import SPECIALISTS
from app.models import AgentRun
from app.services.llm import LLMUnavailable, llm_client

logger = logging.getLogger(__name__)

_SYNTH_SYSTEM = """You are the recommendation engine of a retail analytics platform.
You receive findings gathered by specialist agents from a live database.
Ground every statement in the supplied findings; never invent numbers.
Return JSON only with keys:
rootCause (string), evidence (array of strings), businessImpact (string),
riskLevel ("low"|"medium"|"high"), suggestedCampaign (string),
nextSteps (array of strings)."""


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


def _llm_synthesis(question: str, results: list[AgentResult]) -> dict | None:
    if not llm_client.available:
        return None
    payload = {
        "question": question,
        "findings": [
            {"agent": r.agent, "severity": r.severity,
             "findings": [f.statement for f in r.findings]}
            for r in results
        ],
    }
    try:
        out = llm_client.complete_json(
            system=_SYNTH_SYSTEM, prompt=str(payload), max_tokens=1200)
        out["synthesis"] = "llm"
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM synthesis failed (%s); using rule synthesis.", type(exc).__name__)
        return None


def investigate(db: Session, question: str, *, conversation_id: int | None = None) -> dict:
    """Run the full agent pipeline for a question and return a result payload."""
    started = time.perf_counter()
    plan = build_plan(db, question)
    context = {"question": question, "focus_term": plan["focus_term"]}

    results: list[AgentResult] = []
    for agent_name in plan["agents"]:
        agent_cls = SPECIALISTS.get(agent_name)
        if not agent_cls:
            continue
        try:
            results.append(agent_cls().run(db, context))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent %s failed", agent_name)
            failed = AgentResult(agent=agent_name, task=agent_cls.task)
            failed.data = {"error": type(exc).__name__}
            results.append(failed)

    synthesis = _llm_synthesis(question, results) or _fallback_synthesis(question, results, plan)

    citations = []
    for r in results:
        citations.extend(r.data.get("citations", []))

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
        "agents": [
            {"id": r.agent, "name": SPECIALISTS[r.agent].label if r.agent in SPECIALISTS else r.agent,
             "icon": SPECIALISTS[r.agent].icon if r.agent in SPECIALISTS else "Sparkles",
             "task": r.task, "severity": r.severity, "duration": r.duration_ms,
             "findings": [f.as_dict() for f in r.findings],
             "toolsCalled": r.tools_called}
            for r in results
        ],
        "citations": citations,
        "plan": plan,
        "elapsedMs": int((time.perf_counter() - started) * 1000),
    }

    if conversation_id:
        for r in results:
            db.add(AgentRun(
                conversation_id=conversation_id, agent=r.agent, task=r.task,
                tools_called=r.tools_called,
                findings={"items": [f.as_dict() for f in r.findings]},
                duration_ms=r.duration_ms, status="complete",
            ))
    return result
