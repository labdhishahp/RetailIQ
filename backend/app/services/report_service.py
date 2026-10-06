"""Report generation: composes live analytics into a stored, downloadable report."""

import csv
import io
import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Message, Product, Report
from app.services.analytics_service import analytics_service
from app.services.llm import llm_client

logger = logging.getLogger(__name__)


class ReportService:
    @staticmethod
    def _create(db: Session, **fields) -> Report:
        """Insert a report whose code is derived from its primary key.

        The id comes from the database sequence, so it is unique across
        concurrent requests and never reused after a delete. Counting rows
        (the previous scheme) repeats codes once any report is removed, and
        two simultaneous requests read the same count.
        """
        report = Report(code=f"tmp-{uuid.uuid4().hex[:28]}", **fields)
        db.add(report)
        db.flush()
        report.code = f"RPT-{report.id:04d}"
        db.commit()
        db.refresh(report)
        return report

    def generate(self, db: Session, *, kind: str = "weekly", user_id: int | None = None) -> Report:
        titles = {
            "weekly": "Weekly Executive Summary",
            "monthly": "Monthly Performance Report",
            "inventory": "Inventory Health Report",
            "campaign": "Campaign ROI Analysis",
            "customer": "Customer Segmentation Analysis",
        }
        report = self._create(
            db, title=titles.get(kind, "Business Report"),
            kind=kind, status="generating", created_by_id=user_id,
            period_end=date.today(),
            period_start=date.today() - timedelta(days=30 if kind == "monthly" else 7),
        )

        try:
            payload = self._collect(db, kind)
            report.payload = payload
            report.summary = self._summarise(kind, payload)
            report.status = "ready"
        except Exception:  # noqa: BLE001
            logger.exception("Report generation failed")
            report.status = "failed"
            report.summary = "Report generation failed."
        db.commit()
        db.refresh(report)
        return report

    def _collect(self, db: Session, kind: str) -> dict:
        kpis = analytics_service.kpis(db)
        payload: dict = {"kpis": kpis, "generated_at": datetime.now(timezone.utc).isoformat()}
        if kind in ("weekly", "monthly"):
            payload["revenue_trend"] = analytics_service.revenue_trend(db, 6)
            payload["stores"] = analytics_service.store_comparison(db)
            payload["categories"] = analytics_service.category_sales(db)
            payload["top_products"] = analytics_service.top_products(db, 5)
        if kind in ("inventory", "weekly", "monthly"):
            inv = analytics_service.inventory_overview(db)
            payload["inventory"] = {
                "summary": inv["summary"], "lowStock": inv["lowStock"],
                "deadStock": inv["deadStock"], "reorder": inv["reorderSuggestions"],
            }
        if kind in ("campaign", "weekly", "monthly"):
            payload["campaigns"] = analytics_service.campaign_performance(db)
        if kind == "customer":
            from app.agents.tools import customer_health
            payload["customers"] = customer_health(db)
        return payload

    def _summarise(self, kind: str, payload: dict) -> str:
        k = payload["kpis"]
        base = (
            f"Revenue of {k['revenue']['value']:,.0f} ({k['revenue']['change']:+.1f}%) across "
            f"{int(k['orders']['value'])} orders, with profit of {k['profit']['value']:,.0f} "
            f"({k['profit']['change']:+.1f}%). Business health score {k['healthScore']['value']:.0f}."
        )
        inv = payload.get("inventory", {}).get("summary")
        if inv:
            base += (f" Inventory holds {inv['totalSKUs']} SKUs worth {inv['totalValue']:,.0f} "
                     f"at {inv['fillRate']:.0f}% fill rate and {inv['turnoverRate']}x turnover.")
        low = payload.get("inventory", {}).get("lowStock") or []
        if low:
            base += f" {len(low)} location(s) are below reorder level."
        camps = payload.get("campaigns") or []
        weak = [c for c in camps if c["roi"] < 2.5]
        if weak:
            base += f" {len(weak)} channel(s) are returning below the 2.5x ROI target."

        if llm_client.available:
            try:
                return llm_client.complete(
                    system="Write a concise 3-sentence executive summary for a retail report. "
                           "Use only the supplied figures.",
                    prompt=json.dumps(payload, default=str)[:6000], max_tokens=400).strip()
            except Exception:  # noqa: BLE001
                logger.warning("LLM report summary unavailable; using computed summary.")
        return base

    # -- decision reports --------------------------------------------------
    #
    # Built from a saved investigation (Message.result), so the agents are not
    # re-run. Chart data is recomputed from the live tables at generation time
    # through the same tools the agents use; `data_as_of` and `investigated_at`
    # are both recorded so a reader can see if the data moved in between.

    def generate_decision(self, db: Session, *, message: Message, question: str,
                          user_id: int | None = None) -> Report:
        report = self._create(
            db, title=f"Decision Report: {question[:200]}",
            kind="decision", status="generating", created_by_id=user_id,
            period_end=date.today(),
        )
        try:
            report.payload = self._decision_payload(db, message, question)
            report.summary = (message.result or {}).get("rootCause") or message.content
            report.status = "ready"
        except Exception:  # noqa: BLE001
            logger.exception("Decision report generation failed")
            db.rollback()
            report.status = "failed"
            report.summary = "Report generation failed."
        db.commit()
        db.refresh(report)
        return report

    def _decision_payload(self, db: Session, message: Message, question: str) -> dict:
        result = message.result or {}
        trace = result.get("trace", {})
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_as_of": analytics_service._now(db).isoformat(),
            "source": {"conversation_id": message.conversation_id, "message_id": message.id,
                       "investigated_at": message.created_at.isoformat() if message.created_at else None},
            "question": question,
            "summary": {k: result.get(k) for k in (
                "rootCause", "businessImpact", "riskLevel", "priority", "confidence",
                "revenueImpact", "inventoryImpact", "synthesis")},
            "recommendation": {"action": result.get("suggestedCampaign"),
                               "nextSteps": result.get("nextSteps", [])},
            "evidence": result.get("evidence", []),
            "agents": [
                {k: a.get(k) for k in ("id", "agent", "name", "icon", "task", "objective", "round",
                                       "mode", "severity", "duration", "findings", "toolsCalled",
                                       "steps", "fallback")}
                for a in result.get("agents", [])
            ],
            "trace": {k: trace.get(k) for k in ("mode", "decisions", "delegations", "toolCalls",
                                                 "llmTurns", "tokens", "unverifiedClaims", "fallback")},
            "citations": [{k: c.get(k) for k in ("title", "doc_type", "excerpt")}
                          for c in result.get("citations", [])],
            "charts": self._decision_charts(db, result),
        }

    def _decision_charts(self, db: Session, result: dict) -> list[dict]:
        """Charts for what the investigation looked at, from current table data."""
        from app.agents.tools import call_tool

        agents = result.get("agents", [])
        ran = {a.get("agent") or str(a.get("id", "")).split("-")[0] for a in agents}
        entities = list(dict.fromkeys(
            f["entity"] for a in agents for f in a.get("findings", []) if f.get("entity")))
        known = set(db.scalars(select(Product.sku).where(Product.sku.in_(entities))).all()) if entities else set()
        skus = [e for e in entities if e in known][:2]

        charts: list[dict] = []
        for sku in skus:
            d = call_tool(db, "product_drilldown", sku=sku)
            if d.get("weekly"):
                charts.append({
                    "id": f"weekly-{sku}", "type": "line", "title": f"{d['name']}: weekly units",
                    "subtitle": "Weekly buckets over the last 12 weeks",
                    "source": f"product_drilldown(sku={sku})",
                    "xKey": "week", "lines": [{"key": "units", "name": "Units"}],
                    "data": [{"week": w["week"][5:], "units": w["units"]} for w in d["weekly"]],
                })
            if d.get("by_store"):
                # A product that has not sold in 90 days has all-zero revenue
                # by store; where its stock sits is the informative measure.
                if any(s["revenue_90d"] for s in d["by_store"]):
                    title, key, fmt, value = "revenue by store", "revenue", "currency", "revenue_90d"
                    subtitle = "Last 90 days"
                else:
                    title, key, fmt, value = "units on hand by store", "units", "number", "on_hand"
                    subtitle = "No sales in the last 90 days"
                charts.append({
                    "id": f"stores-{sku}", "type": "bar", "title": f"{d['name']}: {title}",
                    "subtitle": subtitle, "source": f"product_drilldown(sku={sku})",
                    "xKey": "store", "dataKey": key, "format": fmt,
                    "data": [{"store": s["store"], key: s[value]} for s in d["by_store"]],
                })
        if "inventory" in ran:
            rows = [r for r in call_tool(db, "inventory_status", name_contains="")
                    if r["days_cover"] is not None][:8]
            if rows:
                charts.append({
                    "id": "cover", "type": "bar", "title": "Lowest days of stock cover",
                    "subtitle": "Days of cover at 90-day sales velocity",
                    "source": "inventory_status()", "xKey": "product", "dataKey": "days",
                    "format": "number",
                    "data": [{"product": r["name"], "days": r["days_cover"]} for r in rows],
                })
        if "pricing" in ran:
            rows = [r for r in call_tool(db, "pricing_position", name_contains="")
                    if r["units_90d"] > 0 and r["discount_vs_list_pct"] > 0][:8]
            if rows:
                charts.append({
                    "id": "discount", "type": "bar", "title": "Discount vs list price",
                    "subtitle": "% below list, last 90 days", "source": "pricing_position()",
                    "xKey": "product", "dataKey": "discount", "format": "number",
                    "data": [{"product": r["name"], "discount": r["discount_vs_list_pct"]} for r in rows],
                })
        if "campaign" in ran:
            rows = [c for c in call_tool(db, "campaign_status") if c["status"] == "active"]
            if rows:
                charts.append({
                    "id": "roi", "type": "bar", "title": "Active campaign ROI",
                    "subtitle": "Revenue / spend (target 2.5x)", "source": "campaign_status()",
                    "xKey": "campaign", "dataKey": "roi", "format": "number",
                    "data": [{"campaign": c["name"], "roi": c["roi"]} for c in rows],
                })
        if "store" in ran:
            rows = call_tool(db, "store_performance")
            if rows:
                charts.append({
                    "id": "store-growth", "type": "bar", "title": "Store revenue growth",
                    "subtitle": "% change, last 90 days vs prior 90", "source": "store_performance()",
                    "xKey": "store", "dataKey": "growth", "format": "number",
                    "data": [{"store": s["store"], "growth": s["growth"]} for s in rows],
                })
        if "customer" in ran:
            health = call_tool(db, "customer_health")
            if health["segments"]:
                charts.append({
                    "id": "segments", "type": "pie", "title": "Lifetime spend by segment",
                    "subtitle": f"{health['at_risk_count']} customers at risk or churned",
                    "source": "customer_health()",
                    "data": [{"category": s["segment"], "value": s["spend"]} for s in health["segments"]],
                })
        if "sales" in ran and not skus:
            trend = analytics_service.revenue_trend(db, 6)
            if trend:
                charts.append({
                    "id": "revenue", "type": "line", "title": "Monthly revenue",
                    "subtitle": "Last 6 months", "source": "analytics.revenue_trend(months=6)",
                    "xKey": "month", "lines": [{"key": "revenue", "name": "Revenue"}],
                    "data": [{"month": t["month"], "revenue": t["revenue"]} for t in trend],
                })
        return charts

    def _decision_csv(self, w, payload: dict) -> None:
        w.writerow(["Question", payload.get("question", "")])
        w.writerow(["Root cause", (payload.get("summary") or {}).get("rootCause", "")])
        w.writerow(["Recommendation", (payload.get("recommendation") or {}).get("action", "")])
        w.writerow([])
        w.writerow(["Next steps"])
        for step in (payload.get("recommendation") or {}).get("nextSteps", []):
            w.writerow([step])
        w.writerow([])
        w.writerow(["Evidence"])
        for item in payload.get("evidence", []):
            w.writerow([item])
        w.writerow([])
        w.writerow(["Agent", "Round", "Severity", "Finding"])
        for a in payload.get("agents", []):
            for f in a.get("findings") or []:
                w.writerow([a.get("name"), a.get("round"), f.get("severity"), f.get("statement")])
        for chart in payload.get("charts", []):
            w.writerow([])
            w.writerow([chart["title"], chart.get("source", "")])
            if chart["data"]:
                w.writerow(list(chart["data"][0].keys()))
                for row in chart["data"]:
                    w.writerow(list(row.values()))

    def to_csv(self, report: Report) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([report.title])
        w.writerow(["Generated", report.payload.get("generated_at", "")])
        w.writerow([])
        if report.kind == "decision":
            self._decision_csv(w, report.payload)
            return buf.getvalue()
        w.writerow(["Summary"])
        w.writerow([report.summary or ""])
        w.writerow([])
        k = report.payload.get("kpis", {})
        if k:
            w.writerow(["Metric", "Value", "Change %", "Trend"])
            for name, m in k.items():
                w.writerow([name, m.get("value"), m.get("change"), m.get("trend")])
            w.writerow([])
        for section in ("revenue_trend", "stores", "categories", "top_products", "campaigns"):
            rows = report.payload.get(section)
            if not rows:
                continue
            w.writerow([section.replace("_", " ").title()])
            w.writerow(list(rows[0].keys()))
            for r in rows:
                w.writerow(list(r.values()))
            w.writerow([])
        inv = report.payload.get("inventory")
        if inv:
            w.writerow(["Inventory Summary"])
            w.writerow(list(inv["summary"].keys()))
            w.writerow(list(inv["summary"].values()))
        return buf.getvalue()


report_service = ReportService()
