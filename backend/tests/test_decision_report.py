"""Decision Reports: built from a saved investigation, charts recomputed from data."""

from app.agents.tools import call_tool


def _investigate(client, auth, question="Which products need immediate reorder?"):
    r = client.post("/api/v1/copilot/query", headers=auth, json={"question": question})
    assert r.status_code == 200, r.text
    return r.json()


def test_decision_report_from_saved_investigation(client, auth, SessionLocal):
    body = _investigate(client, auth)
    r = client.post("/api/v1/reports/decision", headers=auth, json={"message_id": body["message_id"]})
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["kind"] == "decision" and report["status"] == "ready"
    assert report["summary"] == body["result"]["rootCause"]

    p = client.get(f"/api/v1/reports/{report['id']}", headers=auth).json()["payload"]
    assert p["question"] == "Which products need immediate reorder?"
    assert p["summary"]["rootCause"] == body["result"]["rootCause"]
    assert p["recommendation"]["nextSteps"] == body["result"]["nextSteps"]
    assert [a["id"] for a in p["agents"]] == [a["id"] for a in body["result"]["agents"]]
    assert p["trace"]["decisions"] == body["result"]["trace"]["decisions"]
    assert p["source"]["message_id"] == body["message_id"]

    charts = {c["id"]: c for c in p["charts"]}
    assert charts, "an inventory investigation must produce charts"
    for c in charts.values():
        assert c["data"] and c["source"]

    # Chart values are the tool output at generation time, not fixed numbers.
    db = SessionLocal()
    try:
        cover = [r for r in call_tool(db, "inventory_status", name_contains="")
                 if r["days_cover"] is not None][:8]
        assert charts["cover"]["data"] == [{"product": r["name"], "days": r["days_cover"]} for r in cover]
        if "weekly-T-001" in charts:
            weekly = call_tool(db, "product_drilldown", sku="T-001")["weekly"]
            assert [d["units"] for d in charts["weekly-T-001"]["data"]] == [w["units"] for w in weekly]
    finally:
        db.close()

    csv = client.get(f"/api/v1/reports/{report['id']}/download?fmt=csv", headers=auth)
    assert csv.status_code == 200
    assert "Question" in csv.text and charts["cover"]["title"] in csv.text

    client.delete(f"/api/v1/copilot/conversations/{body['conversation_id']}", headers=auth)


def test_decision_report_rejects_unknown_or_foreign_investigations(client, auth, analyst_token):
    assert client.post("/api/v1/reports/decision", headers=auth,
                       json={"message_id": 999999}).status_code == 404

    body = _investigate(client, auth, "Is there customer churn risk?")
    other = {"Authorization": f"Bearer {analyst_token}"}
    r = client.post("/api/v1/reports/decision", headers=other, json={"message_id": body["message_id"]})
    assert r.status_code == 403

    # The user's own question message is not an investigation result.
    detail = client.get(f"/api/v1/copilot/conversations/{body['conversation_id']}", headers=auth).json()
    user_msg = next(m for m in detail["messages"] if m["role"] == "user")
    assert client.post("/api/v1/reports/decision", headers=auth,
                       json={"message_id": user_msg["id"]}).status_code == 404

    client.delete(f"/api/v1/copilot/conversations/{body['conversation_id']}", headers=auth)


def test_decision_report_requires_auth(client):
    assert client.post("/api/v1/reports/decision", json={"message_id": 1}).status_code == 401


def test_unsold_product_charts_stock_not_zero_revenue(client, auth):
    """Slow Mover has stock and no sales: its store chart must show units on hand."""
    body = _investigate(client, auth, "Which products are dead stock tying up capital?")
    report = client.post("/api/v1/reports/decision", headers=auth,
                         json={"message_id": body["message_id"]}).json()
    charts = {c["id"]: c for c in
              client.get(f"/api/v1/reports/{report['id']}", headers=auth).json()["payload"]["charts"]}
    assert "stores-T-002" in charts, sorted(charts)
    assert charts["stores-T-002"]["dataKey"] == "units"
    assert sum(r["units"] for r in charts["stores-T-002"]["data"]) == 500
    client.delete(f"/api/v1/copilot/conversations/{body['conversation_id']}", headers=auth)


# ---- report codes ---------------------------------------------------------

def _codes(db):
    from sqlalchemy import select

    from app.models import Report
    return dict(db.execute(select(Report.code, Report.id)).all())


def test_report_codes_do_not_collide_after_deletions(client, auth, SessionLocal):
    """Regression: codes were RPT-<row count + 1>, so after earlier reports were
    deleted the next code could already exist (RPT-0003 with two rows left)."""
    from sqlalchemy import delete, func, select

    from app.models import Message, Report
    from app.services.report_service import report_service

    message_id = _investigate(client, auth)["message_id"]
    db = SessionLocal()
    try:
        # Rebuild the failing state: reports whose codes run past the row count.
        db.execute(delete(Report))
        db.commit()
        first = report_service._create(db, title="t", kind="weekly", status="ready")
        while db.scalar(select(func.count()).select_from(Report)) < first.id + 1:
            report_service._create(db, title="t", kind="weekly", status="ready")
        db.execute(delete(Report).where(Report.id == first.id))
        db.commit()
        count = db.scalar(select(func.count()).select_from(Report))
        stale_code = f"RPT-{count + 1:04d}"
        assert stale_code in _codes(db), "precondition: the old scheme's next code exists"

        message = db.get(Message, message_id)
        decision = report_service.generate_decision(db, message=message, question="q")
        weekly = report_service.generate(db, kind="inventory")
        for report in (decision, weekly):
            assert report.status == "ready"
            assert report.code == f"RPT-{report.id:04d}" != stale_code
        codes = _codes(db)
        assert len(codes) == db.scalar(select(func.count()).select_from(Report))
    finally:
        db.close()


def test_concurrent_decision_reports_get_unique_codes(client, auth, SessionLocal):
    from concurrent.futures import ThreadPoolExecutor

    from app.models import Message
    from app.services.report_service import report_service

    message_id = _investigate(client, auth)["message_id"]

    def create(_):
        db = SessionLocal()
        try:
            report = report_service.generate_decision(
                db, message=db.get(Message, message_id), question="q")
            return report.id, report.code, report.status
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        made = list(pool.map(create, range(6)))
    assert all(status == "ready" for _, _, status in made)
    assert len({code for _, code, _ in made}) == 6
    assert all(code == f"RPT-{rid:04d}" for rid, code, _ in made)


# ---- PDF export -----------------------------------------------------------

def _decision_report(client, auth):
    body = _investigate(client, auth)
    report = client.post("/api/v1/reports/decision", headers=auth,
                         json={"message_id": body["message_id"]}).json()
    return body, report


def test_decision_report_downloads_as_pdf(client, auth):
    body, report = _decision_report(client, auth)
    r = client.get(f"/api/v1/reports/{report['id']}/download?fmt=pdf", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="{report["code"]}.pdf"'
    assert r.content.startswith(b"%PDF-") and r.content.rstrip().endswith(b"%%EOF")
    assert r.content.count(b"/Type /Page\n") + r.content.count(b"/Type /Page ") >= 1
    # CSV export still works alongside it
    assert client.get(f"/api/v1/reports/{report['id']}/download?fmt=csv", headers=auth).status_code == 200
    client.delete(f"/api/v1/copilot/conversations/{body['conversation_id']}", headers=auth)


def test_pdf_is_rendered_from_the_saved_report_only(client, auth, SessionLocal, monkeypatch):
    from sqlalchemy import func, select

    import app.agents.orchestrator as orchestrator
    from app.models import AgentRun, Conversation, Message, Report
    from app.services.report_service import report_service

    body, report = _decision_report(client, auth)

    def forbidden(*_, **__):
        raise AssertionError("PDF download must not investigate or recompute charts")

    monkeypatch.setattr(orchestrator, "investigate", forbidden)
    monkeypatch.setattr(report_service, "_decision_charts", forbidden)
    monkeypatch.setattr(report_service, "generate_decision", forbidden)

    db = SessionLocal()
    try:
        counts = lambda: [db.scalar(select(func.count()).select_from(m))  # noqa: E731
                          for m in (Report, Conversation, Message, AgentRun)]
        before = counts()
        r = client.get(f"/api/v1/reports/{report['id']}/download?fmt=pdf", headers=auth)
        assert r.status_code == 200 and r.content.startswith(b"%PDF-")
        db.expire_all()
        assert counts() == before, "downloading must not create reports, conversations or runs"
    finally:
        db.close()
    client.delete(f"/api/v1/copilot/conversations/{body['conversation_id']}", headers=auth)


def test_pdf_missing_or_unsupported_report(client, auth):
    assert client.get("/api/v1/reports/999999/download?fmt=pdf", headers=auth).status_code == 404
    weekly = client.post("/api/v1/reports/generate", headers=auth, json={"kind": "inventory"}).json()
    r = client.get(f"/api/v1/reports/{weekly['id']}/download?fmt=pdf", headers=auth)
    assert r.status_code == 400
    assert client.get("/api/v1/reports/1/download?fmt=pdf").status_code == 401
