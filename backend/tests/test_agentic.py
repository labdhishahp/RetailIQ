"""The agent runtime: observation-driven rule agents, the model-driven tool loop,
fallbacks, and the tool-layer bug fixes found in the audit.

Model-driven runs use a scripted stand-in for the LLM client, so these tests
exercise the real loop, tools and database without calling any API.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agents.base import verify_statement
from app.agents.orchestrator import investigate
from app.agents.tools import ToolError, call_tool
from app.models import Customer, Product, Sale, SaleItem
from app.services.llm import LLMUnavailable


# ---- tool layer -----------------------------------------------------------

def test_tool_rejects_arguments_outside_its_schema(SessionLocal, seeded):
    db = SessionLocal()
    try:
        with pytest.raises(ToolError):
            call_tool(db, "inventory_status", name_contains="x", warehouse="T-DC")
        with pytest.raises(ToolError):
            call_tool(db, "sales_summary", days="ninety")
    finally:
        db.close()


def test_pricing_counts_only_the_last_90_days(db, seeded):
    """Sale lines older than 90 days must not feed the '90d' pricing figures."""
    slow = db.get(Product, seeded["slow_id"])
    old = Sale(store_id=seeded["store_id"], customer_id=seeded["customer_id"],
               sale_number="T-OLD-0001", total_amount=Decimal("125.00"), total_items=5,
               sale_date=datetime.now(timezone.utc) - timedelta(days=200), status="completed")
    db.add(old)
    db.flush()
    db.add(SaleItem(sale_id=old.id, product_id=slow.id, quantity=5, unit_price=Decimal("25.00"),
                    unit_cost=Decimal("25.00"), line_total=Decimal("125.00")))
    db.flush()

    row = next(p for p in call_tool(db, "pricing_position", name_contains="Slow Mover"))
    assert row["units_90d"] == 0
    assert row["discount_vs_list_pct"] == 0.0


def test_customer_health_counts_every_lapsing_customer(db, seeded):
    db.add_all([
        Customer(code=f"T-RISK-{i}", name=f"Risk {i}", email=f"risk{i}@retailiq-test.com",
                 segment="Regular", status="at_risk", total_spent=Decimal("100.00"),
                 last_order_date=date.today() - timedelta(days=120))
        for i in range(10)
    ])
    db.flush()
    health = call_tool(db, "customer_health")
    assert health["at_risk_count"] == 10, "count must not be capped by the top-8 list"
    assert len(health["at_risk"]) == 8
    assert health["at_risk_spend"] == 1000.0


def test_grounding_check():
    observed = [{"on_hand": 15, "days_cover": 7, "revenue_change_pct": -12.34}]
    assert verify_statement("Fast Mover has 15 units, revenue -12.3%.", observed) is True
    assert verify_statement("Fast Mover has 999 units.", observed) is False
    assert verify_statement("Stock is healthy.", observed) is None


# ---- rule-driven investigation -------------------------------------------

def test_rule_lead_follows_up_on_what_it_finds(SessionLocal, seeded):
    """Round 2 is chosen from round-1 findings, and RAG is queried with them."""
    db = SessionLocal()
    try:
        result = investigate(db, "Which products need immediate reorder?")
        trace = result["trace"]
        assert trace["mode"] == "rules"

        inventory = next(a for a in result["agents"] if a["agent"] == "inventory")
        tools = [s["tool"] for s in inventory["steps"]]
        # Fast Mover is ~15 days from a stockout, so the agent drills into it.
        assert tools == ["inventory_status", "product_drilldown"]
        assert inventory["steps"][1]["args"] == {"sku": "T-001"}

        follow = [d for d in trace["decisions"] if d["round"] == 2]
        assert follow, "no follow-up round was planned from the findings"
        # Slow Mover has stock but no sales: pricing is sent to assess a markdown.
        assert (follow[0]["agent"], follow[0]["focus"]) == ("pricing", "Slow Mover")
        assert "Inventory Agent reported dead stock" in follow[0]["reason"]
        # Fast Mover's stock risk is not re-sent to sales: round 1 already covered it.
        assert not any(d["agent"] == "sales" for d in follow)

        knowledge = next(d for d in trace["decisions"] if d["agent"] == "knowledge")
        assert "reorder policy" in knowledge["objective"]
        assert len({a["id"] for a in result["agents"]}) == len(result["agents"])
    finally:
        db.close()


# ---- model-driven investigation (scripted LLM) ---------------------------

def _tool(id_, name, **input_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def _reply(*blocks, stop="tool_use"):
    return SimpleNamespace(stop_reason=stop, content=list(blocks),
                           usage=SimpleNamespace(input_tokens=100, output_tokens=20))


class ScriptedLLM:
    """Replays a fixed reply sequence per agent and records what it was sent."""

    tool_calling_available = True

    def __init__(self, scripts: dict[str, list]):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.calls: dict[str, list[dict]] = {k: [] for k in scripts}

    def create_message(self, *, system, messages, tools=None, effort="medium",
                       max_tokens=16000, timeout=None):
        role = next(k for k in self.scripts if system.startswith(f"You are the {k}"))
        self.calls[role].append({"messages": list(messages),
                                 "tools": [t["name"] for t in tools or []]})
        return self.scripts[role].pop(0)


def _llm_script():
    return {
        "lead investigator": [
            # Round 1: two independent delegations in one turn (run in parallel).
            _reply(_tool("L1", "delegate", agent="inventory", focus="",
                         objective="Find products at risk of stocking out"),
                   _tool("L2", "delegate", agent="knowledge", focus="",
                         objective="reorder policy and cover targets")),
            # Round 2: after reading the findings, a focused follow-up.
            _reply(_tool("L3", "delegate", agent="sales", focus="Fast Mover",
                         objective="Is demand for Fast Mover steady?")),
            # Conclusion without nextSteps: that field must come from the rules.
            _reply(_tool("L4", "submit_conclusion",
                         rootCause="Fast Mover has 15 units on hand against steady demand.",
                         evidence=["Fast Mover has 15 units."], businessImpact="Stockout risk.",
                         riskLevel="high", suggestedCampaign="Reorder Fast Mover now.",
                         nextSteps=[])),
        ],
        "Inventory Agent": [
            _reply(_tool("I1", "campaign_status")),          # outside its scope
            _reply(_tool("I2", "inventory_status", name_contains="")),
            _reply(_tool("I3", "product_drilldown", sku="T-001")),
            _reply(_tool("I4", "submit_findings", summary="Fast Mover is short.", follow_up="",
                         findings=[
                             {"statement": "Fast Mover has 15 units on hand.",
                              "severity": "critical", "entity": "T-001"},
                             {"statement": "Fast Mover will need 999 units.",
                              "severity": "warning", "entity": "T-001"},
                         ])),
        ],
        "Knowledge Agent": [
            _reply(_tool("K1", "search_knowledge_base", query="reorder policy", limit=3)),
            _reply(_tool("K2", "submit_findings", summary="Policy found.", follow_up="",
                         findings=[{"statement": "Reorder at or below the reorder level.",
                                    "severity": "info", "entity": ""}])),
        ],
        "Sales Agent": [
            _reply(_tool("S1", "product_sales_trend", name_contains="Fast Mover", days=30)),
            _reply(_tool("S2", "submit_findings", summary="Demand steady.", follow_up="",
                         findings=[{"statement": "Fast Mover demand is steady.",
                                    "severity": "info", "entity": "T-001"}])),
        ],
    }


def test_model_lead_delegates_observes_and_follows_up(SessionLocal, seeded):
    llm = ScriptedLLM(_llm_script())
    db = SessionLocal()
    try:
        result = investigate(db, "Which products need immediate reorder?", llm=llm)
    finally:
        db.close()

    trace = result["trace"]
    assert trace["mode"] == "llm" and result["plan"]["planner"] == "llm"
    assert [(d["round"], d["agent"]) for d in trace["decisions"]] == [
        (1, "inventory"), (1, "knowledge"), (2, "sales")]

    inventory = next(a for a in result["agents"] if a["agent"] == "inventory")
    assert inventory["mode"] == "llm"
    # The out-of-scope call was refused and the agent carried on with its own tools.
    assert [s["tool"] for s in inventory["steps"] if s["ok"]] == ["inventory_status", "product_drilldown"]
    assert inventory["toolsCalled"] == ["inventory_status", "product_drilldown"]
    refused = llm.calls["Inventory Agent"][1]["messages"][-1]["content"][0]
    assert refused["tool_use_id"] == "I1" and refused["is_error"] is True
    # Each specialist is offered only its own tools plus its finishing tool.
    assert llm.calls["Inventory Agent"][0]["tools"] == [
        "inventory_status", "product_drilldown", "submit_findings"]

    verified = {f["statement"]: f["verified"] for f in inventory["findings"]}
    assert verified["Fast Mover has 15 units on hand."] is True
    assert verified["Fast Mover will need 999 units."] is False

    # The lead saw the round-1 findings before choosing its follow-up.
    seen = str(llm.calls["lead investigator"][1]["messages"][-1]["content"])
    assert "Fast Mover has 15 units on hand." in seen

    assert result["synthesis"] == "llm_partial"
    assert result["rootCause"].startswith("Fast Mover has 15 units")
    assert result["nextSteps"], "missing model fields fall back to the rule synthesis"
    assert result["citations"], "knowledge agent retrieved documents"
    assert trace["tokens"] > 0 and trace["llmTurns"] == 3 + 4 + 2 + 2


class BrokenLLM:
    tool_calling_available = True

    def create_message(self, **_):
        raise LLMUnavailable("APIConnectionError: unreachable")


def test_unreachable_model_falls_back_to_rule_investigation(SessionLocal, seeded):
    db = SessionLocal()
    try:
        result = investigate(db, "Which products need immediate reorder?", llm=BrokenLLM())
    finally:
        db.close()
    assert result["trace"]["mode"] == "rules"
    assert "unreachable" in result["trace"]["fallback"]
    assert result["synthesis"] == "rules"
    assert any(a["toolsCalled"] for a in result["agents"])
