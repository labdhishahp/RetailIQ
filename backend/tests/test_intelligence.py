"""Analytics, RAG retrieval, the agent pipeline, simulation and recommendations."""

import pytest

from app.agents.orchestrator import investigate
from app.agents.planner import build_plan
from app.agents.tools import TOOLS, call_tool
from app.services.analytics_service import analytics_service
from app.services.embedding import chunk_text, embed
from app.services.rag_service import rag_service
from app.services.recommendation_service import recommendation_service
from app.services.simulation_service import simulation_service


# ---- embeddings ---------------------------------------------------------

def test_embedding_is_deterministic_and_normalised():
    a, b = embed("reorder level stock cover"), embed("reorder level stock cover")
    assert a == b
    assert len(a) == 384
    assert abs(sum(x * x for x in a) ** 0.5 - 1.0) < 1e-6


def test_embedding_similar_text_is_closer_than_unrelated():
    def cos(u, v):
        return sum(x * y for x, y in zip(u, v))
    base = embed("purchase order reorder level replenishment stock")
    near = embed("replenishment reorder stock purchase")
    far = embed("customer churn email marketing segment")
    assert cos(base, near) > cos(base, far)


def test_empty_text_yields_a_usable_vector():
    v = embed("")
    assert len(v) == 384 and any(v)


def test_chunking_covers_the_document():
    text = "\n\n".join(f"Paragraph {i} with some body text." for i in range(40))
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


# ---- RAG ----------------------------------------------------------------

def test_rag_retrieves_the_relevant_document(SessionLocal, seeded):
    db = SessionLocal()
    try:
        hits = rag_service.search(db, "when should a purchase order be raised", limit=3)
        assert hits, "hybrid search returned nothing"
        assert any("Replenishment" in h["title"] for h in hits)
        assert hits[0]["score"] >= hits[-1]["score"]
    finally:
        db.close()


def test_rag_empty_query_returns_nothing(SessionLocal):
    db = SessionLocal()
    try:
        assert rag_service.search(db, "   ") == []
    finally:
        db.close()


def test_rag_endpoint_requires_auth(client):
    assert client.get("/api/v1/copilot/search?q=stock").status_code == 401


def test_document_ingest_creates_chunks(client, auth):
    r = client.post("/api/v1/copilot/documents", headers=auth, json={
        "title": "Ephemeral Policy",
        "doc_type": "policy",
        "content": "Markdowns require category manager approval above fifteen percent. " * 10,
    })
    assert r.status_code == 201
    doc_id = r.json()["id"]
    stats = client.get("/api/v1/copilot/knowledge-stats", headers=auth).json()
    assert stats["chunks"] > 0
    assert client.delete(f"/api/v1/copilot/documents/{doc_id}", headers=auth).status_code == 204


# ---- analytics ----------------------------------------------------------

def test_kpis_shape_and_types(SessionLocal, seeded):
    db = SessionLocal()
    try:
        k = analytics_service.kpis(db)
        assert set(k) == {"revenue", "orders", "profit", "healthScore"}
        for metric in k.values():
            assert isinstance(metric["value"], (int, float))
            assert metric["trend"] in {"up", "down"}
    finally:
        db.close()


def test_revenue_trend_length_is_bounded(SessionLocal, seeded):
    db = SessionLocal()
    try:
        assert len(analytics_service.revenue_trend(db, 12)) <= 12
    finally:
        db.close()


def test_products_overview_computes_margin(SessionLocal, seeded):
    db = SessionLocal()
    try:
        rows = analytics_service.products_overview(db)
        fast = next(r for r in rows if r["id"] == "T-001")
        # price 20, cost 8 -> 60%
        assert fast["margin"] == pytest.approx(60.0, abs=0.1)
        assert isinstance(fast["price"], float)
        assert fast["stock"] > 0
    finally:
        db.close()


def test_inventory_overview_flags_below_reorder(SessionLocal, seeded):
    db = SessionLocal()
    try:
        overview = analytics_service.inventory_overview(db)
        assert overview["summary"]["totalSKUs"] >= 2
        # fast mover: 30 on hand vs reorder level 100
        assert any(r["id"] == "T-001" for r in overview["lowStock"])
        assert all("product_id" in r for r in overview["reorderSuggestions"])
    finally:
        db.close()


def test_money_serialises_as_json_number(client, auth):
    row = client.get("/api/v1/analytics/products-overview", headers=auth).json()[0]
    assert isinstance(row["price"], (int, float))
    assert not isinstance(row["price"], str)


# ---- agent tools --------------------------------------------------------

@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_every_tool_executes(SessionLocal, seeded, tool):
    """A broken tool must fail loudly here, not silently inside an agent."""
    db = SessionLocal()
    try:
        kwargs = {"query": "stock"} if tool == "search_knowledge_base" else {}
        result = call_tool(db, tool, **kwargs)
        assert result is not None
    finally:
        db.close()


def test_unknown_tool_raises(SessionLocal):
    db = SessionLocal()
    try:
        with pytest.raises(KeyError):
            call_tool(db, "no_such_tool")
    finally:
        db.close()


# ---- planner + orchestrator --------------------------------------------

@pytest.mark.parametrize("question,expected", [
    ("Which products need immediate reorder?", "inventory"),
    ("Is there customer churn risk?", "customer"),
    ("How is the campaign performing?", "campaign"),
    ("Are our margins under pressure?", "pricing"),
    ("Compare store performance", "store"),
])
def test_planner_routes_by_intent(SessionLocal, seeded, question, expected):
    db = SessionLocal()
    try:
        plan = build_plan(db, question)
        assert expected in plan["agents"]
        assert "knowledge" in plan["agents"], "RAG must always be consulted"
    finally:
        db.close()


def test_planner_extracts_a_real_product_as_focus(SessionLocal, seeded):
    db = SessionLocal()
    try:
        plan = build_plan(db, "why are Fast Mover sales falling?")
        assert plan["focus_term"]
    finally:
        db.close()


def test_investigation_is_grounded_and_complete(SessionLocal, seeded):
    db = SessionLocal()
    try:
        result = investigate(db, "Which products need immediate reorder?")
        for key in ("rootCause", "evidence", "confidence", "riskLevel",
                    "suggestedCampaign", "nextSteps", "agents", "citations"):
            assert key in result, f"missing {key}"
        assert result["agents"], "no agent ran"
        assert 35 <= result["confidence"] <= 95
        assert result["riskLevel"] in {"low", "medium", "high"}
        # findings must cite real tool output, so at least one tool was called
        assert any(a["toolsCalled"] for a in result["agents"])
    finally:
        db.close()


def test_different_questions_produce_different_answers(SessionLocal, seeded):
    db = SessionLocal()
    try:
        a = investigate(db, "Which products need immediate reorder?")
        b = investigate(db, "Is there customer churn risk?")
        assert a["rootCause"] != b["rootCause"], "answer is not question-dependent"
        assert {x["id"] for x in a["agents"]} != {x["id"] for x in b["agents"]}
    finally:
        db.close()


def test_copilot_endpoint_persists_the_conversation(client, auth):
    r = client.post("/api/v1/copilot/query", headers=auth,
                    json={"question": "Which products need immediate reorder?"})
    assert r.status_code == 200
    body = r.json()
    convo_id = body["conversation_id"]

    detail = client.get(f"/api/v1/copilot/conversations/{convo_id}", headers=auth).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    assert client.delete(f"/api/v1/copilot/conversations/{convo_id}",
                         headers=auth).status_code == 204


# ---- simulation ---------------------------------------------------------

def test_simulation_discount_lifts_units(SessionLocal, seeded):
    db = SessionLocal()
    try:
        out = simulation_service.run(
            db, name="t", discount_pct=20, duration_days=30,
            product_skus=["T-001"], persist=False)
        assert out["results"]["sales"]["change"] > 0, "a discount must raise unit demand"
        assert out["results"]["products"][0]["promo_price"] < out["results"]["products"][0]["list_price"]
    finally:
        db.close()


def test_zero_discount_is_neutral(SessionLocal, seeded):
    db = SessionLocal()
    try:
        out = simulation_service.run(
            db, name="t", discount_pct=0, duration_days=30,
            product_skus=["T-001"], persist=False)
        assert out["results"]["sales"]["change"] == pytest.approx(0, abs=0.5)
    finally:
        db.close()


def test_deeper_discount_lifts_units_more(SessionLocal, seeded):
    db = SessionLocal()
    try:
        small = simulation_service.run(db, name="t", discount_pct=10, duration_days=30,
                                       product_skus=["T-001"], persist=False)
        large = simulation_service.run(db, name="t", discount_pct=30, duration_days=30,
                                       product_skus=["T-001"], persist=False)
        assert large["results"]["sales"]["change"] > small["results"]["sales"]["change"]
    finally:
        db.close()


def test_simulation_rejects_empty_selection(SessionLocal, seeded):
    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            simulation_service.run(db, name="t", discount_pct=10, duration_days=10,
                                   product_skus=["DOES-NOT-EXIST"], persist=False)
    finally:
        db.close()


def test_simulation_endpoint_validates_input(client, auth):
    assert client.post("/api/v1/simulations/run", headers=auth, json={
        "discount_pct": 150, "duration_days": 30}).status_code == 422


# ---- recommendations ----------------------------------------------------

def test_recommendations_detect_stockout_risk(SessionLocal, seeded):
    db = SessionLocal()
    try:
        recommendation_service.generate(db)
        from sqlalchemy import select
        from app.models import Recommendation
        recs = db.scalars(select(Recommendation)).all()
        assert any(r.kind == "stockout_risk" for r in recs), "fast mover should trigger reorder"
        for r in recs:
            assert r.title and r.rationale and 0 < r.confidence <= 100
    finally:
        db.close()


def test_recommendation_sweep_is_idempotent(SessionLocal, seeded):
    db = SessionLocal()
    try:
        recommendation_service.generate(db)
        second = recommendation_service.generate(db)
        assert second == [], "re-running must not duplicate open recommendations"
    finally:
        db.close()


def test_accepting_a_recommendation_logs_a_decision(client, auth):
    recs = client.get("/api/v1/recommendations?status=pending", headers=auth).json()
    if not recs:
        pytest.skip("no pending recommendations in the test dataset")
    before = len(client.get("/api/v1/decisions", headers=auth).json())
    r = client.post(f"/api/v1/recommendations/{recs[0]['id']}/action",
                    headers=auth, json={"status": "accepted"})
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    after = client.get("/api/v1/decisions", headers=auth).json()
    assert len(after) == before + 1
