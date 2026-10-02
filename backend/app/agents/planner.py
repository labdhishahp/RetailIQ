"""First-round routing for the rule-based lead investigator, and focus extraction.

This is only where a rule-driven investigation *starts*: which specialists to
send first, and which product the question is about. Later rounds are chosen
from what those specialists find (orchestrator._follow_ups). When a model is
configured, the lead investigator plans for itself and uses the focus found
here only as a hint.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Product

_INTENT_AGENTS: list[tuple[str, re.Pattern, list[str]]] = [
    ("stock", re.compile(r"stock|inventor|reorder|stockout|warehouse|dead stock|overstock", re.I),
     ["inventory", "sales", "knowledge"]),
    ("pricing", re.compile(r"price|pricing|margin|discount|cost|profitab", re.I),
     ["pricing", "sales", "knowledge"]),
    ("campaign", re.compile(r"campaign|marketing|roi|ad spend|promotion", re.I),
     ["campaign", "sales", "knowledge"]),
    ("customer", re.compile(r"customer|churn|segment|retention|loyalty|vip", re.I),
     ["customer", "sales", "knowledge"]),
    ("store", re.compile(r"store|location|region|branch|outlet", re.I),
     ["store", "sales", "knowledge"]),
    ("decline", re.compile(r"declin|decreas|drop|fall|down|why|underperform|lost", re.I),
     ["sales", "inventory", "pricing", "campaign", "customer", "knowledge"]),
]

_DEFAULT_PLAN = ["sales", "inventory", "campaign", "knowledge"]


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
    for intent, pattern, agents in _INTENT_AGENTS:
        if pattern.search(question):
            return {"agents": list(agents), "focus_term": focus, "intent": intent,
                    "reason": f"question matches the {intent} intent", "planner": "rules"}
    return {"agents": list(_DEFAULT_PLAN), "focus_term": focus, "intent": "overview",
            "reason": "no specific intent; starting with a broad sweep", "planner": "rules"}
