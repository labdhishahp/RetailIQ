"""Decides which specialists to run for a question, and extracts the focus.

Uses the LLM when configured; otherwise a keyword/intent classifier. Both
paths return the same plan structure, so orchestration is identical.
"""

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.specialists import SPECIALISTS
from app.models import Category, Product
from app.services.llm import LLMUnavailable, llm_client

logger = logging.getLogger(__name__)

_INTENT_AGENTS: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"stock|inventor|reorder|stockout|warehouse|dead stock|overstock", re.I),
     ["inventory", "sales", "knowledge"]),
    (re.compile(r"price|pricing|margin|discount|cost|profitab", re.I),
     ["pricing", "sales", "knowledge"]),
    (re.compile(r"campaign|marketing|roi|ad spend|promotion", re.I),
     ["campaign", "sales", "knowledge"]),
    (re.compile(r"customer|churn|segment|retention|loyalty|vip", re.I),
     ["customer", "sales", "knowledge"]),
    (re.compile(r"store|location|region|branch|outlet", re.I),
     ["store", "sales", "knowledge"]),
    (re.compile(r"declin|decreas|drop|fall|down|why|underperform|lost", re.I),
     ["sales", "inventory", "pricing", "campaign", "customer", "knowledge"]),
]

_DEFAULT_PLAN = ["sales", "inventory", "campaign", "knowledge"]

_SYSTEM = """You plan investigations for a retail analytics copilot.
Given a business question, choose which specialist agents should run.
Available agents: sales, inventory, pricing, campaign, customer, store, knowledge.
Always include "knowledge". Return JSON only:
{"agents": ["..."], "focus_term": "<product or category name mentioned, else empty>",
 "intent": "<one short phrase>"}"""


def _extract_focus(db: Session, question: str) -> str:
    """Match the question against real product and category names."""
    q = question.lower()
    names = db.execute(select(Product.name)).scalars().all()
    for name in names:
        if name.lower() in q:
            return name
        head = name.split()[0].lower()
        if len(head) > 4 and head in q:
            return head
    for cat in db.execute(select(Category.name)).scalars().all():
        if cat.lower() in q:
            return ""  # category-wide: do not narrow product filters
    # fall back to any noun-ish token that matches a product substring
    for token in re.findall(r"[a-z]{5,}", q):
        hit = db.scalar(
            select(func.count()).select_from(Product).where(Product.name.ilike(f"%{token}%")))
        if hit:
            return token
    return ""


def build_plan(db: Session, question: str) -> dict:
    focus = _extract_focus(db, question)

    if llm_client.available:
        try:
            plan = llm_client.complete_json(
                system=_SYSTEM, prompt=f"Question: {question}", max_tokens=300)
            agents = [a for a in plan.get("agents", []) if a in SPECIALISTS]
            if agents:
                if "knowledge" not in agents:
                    agents.append("knowledge")
                return {
                    "agents": agents,
                    "focus_term": plan.get("focus_term") or focus,
                    "intent": plan.get("intent", "investigation"),
                    "planner": "llm",
                }
        except (LLMUnavailable, Exception) as exc:  # noqa: BLE001
            logger.warning("LLM planner unavailable (%s); using rule planner.", type(exc).__name__)

    for pattern, agents in _INTENT_AGENTS:
        if pattern.search(question):
            return {"agents": agents, "focus_term": focus,
                    "intent": "diagnostic", "planner": "rules"}
    return {"agents": _DEFAULT_PLAN, "focus_term": focus,
            "intent": "overview", "planner": "rules"}
