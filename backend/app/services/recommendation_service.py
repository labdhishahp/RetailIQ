"""Generates business recommendations from live data.

Rules evaluate the operational tables and persist a Recommendation per
detected condition, keyed so re-running does not duplicate open items.
"""

import logging
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Campaign, Customer, Inventory, Product, Recommendation
from app.services.analytics_service import _f, _pct_change, analytics_service

logger = logging.getLogger(__name__)


class RecommendationService:
    def generate(self, db: Session) -> list[Recommendation]:
        """(Re)evaluate all rules. Returns newly created recommendations."""
        existing = {
            r.code for r in db.scalars(
                select(Recommendation).where(Recommendation.status == "pending")).all()
        }
        created: list[Recommendation] = []
        for rec in (
            self._stockout_risk(db) + self._dead_stock(db) + self._margin_erosion(db)
            + self._category_decline(db) + self._campaign_roi(db) + self._churn_risk(db)
        ):
            if rec.code in existing:
                continue
            db.add(rec)
            created.append(rec)
        db.commit()
        logger.info("Recommendation sweep created %d new item(s).", len(created))
        return created

    # -- rules -----------------------------------------------------------

    def _stockout_risk(self, db: Session) -> list[Recommendation]:
        velocity = analytics_service._daily_velocity(db)
        rows = db.execute(
            select(Product.id, Product.sku, Product.name, Product.cost, Product.price,
                   func.sum(Inventory.quantity_on_hand), func.sum(Inventory.reorder_quantity))
            .select_from(Inventory).join(Product, Product.id == Inventory.product_id)
            .group_by(Product.id, Product.sku, Product.name, Product.cost, Product.price)
        ).all()
        out = []
        for pid, sku, name, cost, price, qty, rq in rows:
            v = velocity.get(pid, 0.0)
            qty, rq = int(qty or 0), int(rq or 0)
            if v <= 0:
                continue
            days = int(qty / v)
            if days >= 21:
                continue
            lost = round(v * 30 * _f(price), 2)
            out.append(Recommendation(
                code=f"REC-STOCK-{sku}", kind="stockout_risk",
                title=f"Reorder {name} — {days} days of cover left",
                rationale=(f"{name} has {qty} units on hand selling at {v:.1f}/day, giving about "
                           f"{days} days of cover. A stockout would forgo roughly "
                           f"{lost:,.0f} of revenue over the following month."),
                impact=f"Protect ~{lost:,.0f} revenue", revenue_impact=lost,
                confidence=90 if days < 10 else 78,
                priority="critical" if days < 10 else "high",
                evidence={"on_hand": qty, "daily_velocity": round(v, 2),
                          "days_cover": days, "suggested_qty": rq},
                product_id=pid,
            ))
        return out

    def _dead_stock(self, db: Session) -> list[Recommendation]:
        now = analytics_service._now(db)
        velocity = analytics_service._daily_velocity(db, days=60)
        rows = db.execute(
            select(Product.id, Product.sku, Product.name, Product.cost,
                   func.sum(Inventory.quantity_on_hand))
            .select_from(Inventory).join(Product, Product.id == Inventory.product_id)
            .group_by(Product.id, Product.sku, Product.name, Product.cost)
        ).all()
        out = []
        for pid, sku, name, cost, qty in rows:
            qty = int(qty or 0)
            if qty <= 0 or velocity.get(pid, 0.0) > 0:
                continue
            tied = round(qty * _f(cost), 2)
            if tied < 500:
                continue
            out.append(Recommendation(
                code=f"REC-DEAD-{sku}", kind="dead_stock",
                title=f"Liquidate dead stock: {name}",
                rationale=(f"{name} has {qty} units on hand with no sales recorded in the last 60 "
                           f"days, tying up {tied:,.0f} in working capital."),
                impact=f"Recover up to {tied * 0.6:,.0f}", revenue_impact=round(tied * 0.6, 2),
                confidence=72, priority="medium",
                evidence={"units": qty, "capital_tied": tied, "days_idle": 60},
                product_id=pid,
            ))
        return out

    def _margin_erosion(self, db: Session) -> list[Recommendation]:
        from app.agents.tools import pricing_position
        out = []
        for p in pricing_position(db):
            if p["units_90d"] == 0 or p["discount_vs_list_pct"] < 8:
                continue
            product = db.scalar(select(Product).where(Product.sku == p["sku"]))
            leak = round(p["units_90d"] * (p["list_price"] - p["avg_selling_price"]), 2)
            out.append(Recommendation(
                code=f"REC-MARGIN-{p['sku']}", kind="margin_erosion",
                title=f"Margin leak on {p['name']}",
                rationale=(f"{p['name']} sold {p['units_90d']} units at an average of "
                           f"{p['avg_selling_price']:,.2f} against a list price of "
                           f"{p['list_price']:,.2f} — {p['discount_vs_list_pct']:.1f}% below list, "
                           f"about {leak:,.0f} of forgone margin over 90 days."),
                impact=f"Recover ~{leak:,.0f} margin", revenue_impact=leak,
                confidence=70, priority="medium",
                evidence={"list_price": p["list_price"], "avg_price": p["avg_selling_price"],
                          "units": p["units_90d"], "realised_margin": p["realised_margin_pct"]},
                product_id=product.id if product else None,
            ))
        return out

    def _category_decline(self, db: Session) -> list[Recommendation]:
        from app.agents.tools import category_performance
        out = []
        for c in category_performance(db):
            if c["change_pct"] >= -8:
                continue
            loss = round(abs(c["revenue"] * c["change_pct"] / 100), 2)
            out.append(Recommendation(
                code=f"REC-CAT-{c['category'][:12].upper().replace(' ', '')}",
                kind="category_decline",
                title=f"{c['category']} revenue down {abs(c['change_pct']):.1f}%",
                rationale=(f"{c['category']} generated {c['revenue']:,.0f} in the last 90 days, "
                           f"{c['change_pct']:+.1f}% versus the prior period — roughly "
                           f"{loss:,.0f} of lost revenue."),
                impact=f"Recover ~{loss:,.0f}", revenue_impact=loss,
                confidence=75, priority="high" if c["change_pct"] < -15 else "medium",
                evidence={"revenue": c["revenue"], "change_pct": c["change_pct"],
                          "share_pct": c["share_pct"]},
            ))
        return out

    def _campaign_roi(self, db: Session) -> list[Recommendation]:
        out = []
        for c in db.scalars(select(Campaign).where(Campaign.status == "active")).all():
            spent, revenue = _f(c.spent), _f(c.revenue)
            if spent <= 0:
                continue
            roi = revenue / spent
            if roi >= 2.5:
                continue
            upside = round(spent * (2.5 - roi), 2)
            out.append(Recommendation(
                code=f"REC-CAMP-{c.code}", kind="campaign_roi",
                title=f"Reallocate budget from '{c.name}' ({roi:.1f}x ROI)",
                rationale=(f"'{c.name}' on {c.channel} has spent {spent:,.0f} returning "
                           f"{revenue:,.0f} — {roi:.1f}x against a 2.5x target."),
                impact=f"Upside ~{upside:,.0f}", revenue_impact=upside,
                confidence=68, priority="high" if roi < 1.5 else "medium",
                evidence={"spent": spent, "revenue": revenue, "roi": round(roi, 2),
                          "channel": c.channel},
            ))
        return out

    def _churn_risk(self, db: Session) -> list[Recommendation]:
        rows = db.scalars(
            select(Customer).where(Customer.status.in_(["at_risk", "churned"]))
            .order_by(Customer.total_spent.desc()).limit(1)
        ).all()
        if not rows:
            return []
        exposure = _f(db.scalar(
            select(func.coalesce(func.sum(Customer.total_spent), 0))
            .where(Customer.status.in_(["at_risk", "churned"]))))
        count = db.scalar(
            select(func.count()).select_from(Customer)
            .where(Customer.status.in_(["at_risk", "churned"]))) or 0
        if exposure < 1000:
            return []
        return [Recommendation(
            code="REC-CHURN-ALL", kind="churn_risk",
            title=f"Win back {count} lapsed customers",
            rationale=(f"{count} customers are flagged at risk or churned, together representing "
                       f"{exposure:,.0f} of historic spend."),
            impact=f"Protect ~{exposure * 0.3:,.0f}", revenue_impact=round(exposure * 0.3, 2),
            confidence=65, priority="medium",
            evidence={"customers": count, "lifetime_spend": round(exposure, 2)},
        )]

    # -- actions ---------------------------------------------------------

    def resolve(self, db: Session, rec_id: int, *, status: str, user_id: int | None) -> Recommendation | None:
        from datetime import datetime, timezone
        rec = db.get(Recommendation, rec_id)
        if not rec:
            return None
        rec.status = status
        rec.resolved_at = datetime.now(timezone.utc)
        rec.resolved_by_id = user_id
        db.commit()
        db.refresh(rec)
        return rec


recommendation_service = RecommendationService()
