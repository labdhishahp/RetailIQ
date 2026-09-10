"""Report generation: composes live analytics into a stored, downloadable report."""

import csv
import io
import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Report
from app.services.analytics_service import analytics_service
from app.services.llm import llm_client

logger = logging.getLogger(__name__)


class ReportService:
    def generate(self, db: Session, *, kind: str = "weekly", user_id: int | None = None) -> Report:
        count = db.scalar(select(func.count()).select_from(Report)) or 0
        titles = {
            "weekly": "Weekly Executive Summary",
            "monthly": "Monthly Performance Report",
            "inventory": "Inventory Health Report",
            "campaign": "Campaign ROI Analysis",
            "customer": "Customer Segmentation Analysis",
        }
        report = Report(
            code=f"RPT-{count + 1:04d}", title=titles.get(kind, "Business Report"),
            kind=kind, status="generating", created_by_id=user_id,
            period_end=date.today(),
            period_start=date.today() - timedelta(days=30 if kind == "monthly" else 7),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

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

    def to_csv(self, report: Report) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([report.title])
        w.writerow(["Generated", report.payload.get("generated_at", "")])
        w.writerow([])
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
