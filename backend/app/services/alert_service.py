"""Generates alerts and notifications from live conditions."""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Campaign, Customer, Inventory, Product
from app.services.analytics_service import _f, analytics_service

logger = logging.getLogger(__name__)


class AlertService:
    def evaluate(self, db: Session) -> list[Alert]:
        """Evaluate all alert rules. Dedupe keys prevent repeat noise."""
        existing = set(db.scalars(select(Alert.dedupe_key)).all())
        new: list[Alert] = []

        velocity = analytics_service._daily_velocity(db)
        rows = db.execute(
            select(Product.id, Product.name,
                   func.sum(Inventory.quantity_on_hand), func.sum(Inventory.reorder_level))
            .select_from(Inventory).join(Product, Product.id == Inventory.product_id)
            .group_by(Product.id, Product.name)
        ).all()

        for pid, name, qty, lvl in rows:
            qty, lvl = int(qty or 0), int(lvl or 0)
            v = velocity.get(pid, 0.0)
            days = int(qty / v) if v > 0 else None
            if days is not None and days < 14:
                key = f"stock:{pid}:{days // 7}"
                if key not in existing:
                    new.append(Alert(
                        severity="critical" if days < 7 else "warning", category="stock",
                        title=f"Low stock: {name}",
                        message=f"{qty} units remaining — about {days} days of cover at current velocity.",
                        dedupe_key=key, product_id=pid))
            elif qty <= lvl and lvl > 0:
                key = f"reorder:{pid}"
                if key not in existing:
                    new.append(Alert(
                        severity="warning", category="stock",
                        title=f"Reorder threshold breached: {name}",
                        message=f"{qty} units on hand against a reorder level of {lvl}.",
                        dedupe_key=key, product_id=pid))

        for c in db.scalars(select(Campaign).where(Campaign.status == "active")).all():
            spent, revenue = _f(c.spent), _f(c.revenue)
            if spent > 0 and revenue / spent < 2.5:
                key = f"campaign:{c.code}"
                if key not in existing:
                    new.append(Alert(
                        severity="warning", category="campaign",
                        title=f"Campaign ROI below target: {c.name}",
                        message=f"Returning {revenue / spent:.1f}x against a 2.5x target on {spent:,.0f} spent.",
                        dedupe_key=key))
            if c.budget and spent / _f(c.budget) > 0.9:
                key = f"budget:{c.code}"
                if key not in existing:
                    new.append(Alert(
                        severity="info", category="campaign",
                        title=f"Campaign budget nearly exhausted: {c.name}",
                        message=f"{spent / _f(c.budget) * 100:.0f}% of budget spent.",
                        dedupe_key=key))

        churn = db.scalar(
            select(func.count()).select_from(Customer)
            .where(Customer.status.in_(["at_risk", "churned"]))) or 0
        if churn:
            key = f"churn:{churn // 5}"
            if key not in existing:
                new.append(Alert(
                    severity="warning", category="customer",
                    title="Customer churn risk detected",
                    message=f"{churn} customers are flagged at risk or churned.",
                    dedupe_key=key))

        for a in new:
            db.add(a)
        db.commit()
        logger.info("Alert sweep raised %d new alert(s).", len(new))
        return new

    def list_alerts(self, db: Session, *, limit: int = 40, unread_only: bool = False):
        q = select(Alert).order_by(Alert.occurred_at.desc()).limit(limit)
        if unread_only:
            q = q.where(Alert.is_read.is_(False))
        return db.scalars(q).all()

    def mark_read(self, db: Session, alert_id: int) -> Alert | None:
        alert = db.get(Alert, alert_id)
        if alert:
            alert.is_read = True
            db.commit()
            db.refresh(alert)
        return alert

    def mark_all_read(self, db: Session) -> int:
        rows = db.scalars(select(Alert).where(Alert.is_read.is_(False))).all()
        for a in rows:
            a.is_read = True
        db.commit()
        return len(rows)


alert_service = AlertService()
