"""What-if scenario forecasting.

Projects the effect of a discount campaign on units, revenue, margin and
stock cover using price elasticity estimated from the product's own sales
history where possible, falling back to a category-level default.
"""

import logging
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Inventory, Product, Sale, SaleItem, Simulation
from app.services.analytics_service import _f, analytics_service

logger = logging.getLogger(__name__)

# Fallback elasticities by category (negative: demand rises as price falls)
DEFAULT_ELASTICITY = {
    "Groceries": -1.9, "Personal Care": -1.6, "Apparel": -1.4,
    "Electronics": -1.2, "Home & Living": -1.1, "Sports & Outdoors": -1.3,
}
GENERIC_ELASTICITY = -1.4


class SimulationService:
    def _estimate_elasticity(self, db: Session, product_id: int, category: str) -> tuple[float, str]:
        """Regress observed unit volume against realised price by month.

        Needs at least three distinct price points to be meaningful; otherwise
        the category default is used and reported as such.
        """
        bucket = func.date_trunc("month", Sale.sale_date)
        rows = db.execute(
            select(bucket,
                   func.avg(SaleItem.unit_price),
                   func.sum(SaleItem.quantity))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(SaleItem.product_id == product_id)
            .group_by(bucket).having(func.sum(SaleItem.quantity) > 0)
        ).all()

        points = [(_f(p), float(q)) for _, p, q in rows if p and q]
        distinct_prices = {round(p, 2) for p, _ in points}
        if len(points) >= 3 and len(distinct_prices) >= 3:
            n = len(points)
            mean_p = sum(p for p, _ in points) / n
            mean_q = sum(q for _, q in points) / n
            cov = sum((p - mean_p) * (q - mean_q) for p, q in points)
            var = sum((p - mean_p) ** 2 for p, _ in points)
            if var > 0 and mean_q > 0:
                slope = cov / var
                elasticity = slope * mean_p / mean_q
                if -6 < elasticity < -0.2:
                    return round(elasticity, 2), "observed"
        return DEFAULT_ELASTICITY.get(category, GENERIC_ELASTICITY), "category_default"

    def run(
        self,
        db: Session,
        *,
        name: str,
        discount_pct: float,
        duration_days: int,
        product_skus: list[str] | None = None,
        category: str | None = None,
        extra_spend: float = 0.0,
        user_id: int | None = None,
        persist: bool = True,
    ) -> dict:
        q = select(Product, Category.name).join(Category, Category.id == Product.category_id)
        if product_skus:
            q = q.where(Product.sku.in_(product_skus))
        elif category:
            q = q.where(Category.name == category)
        targets = db.execute(q).all()
        if not targets:
            raise ValueError("No products matched the scenario selection")

        velocity = analytics_service._daily_velocity(db)
        stock = dict(db.execute(
            select(Inventory.product_id, func.coalesce(func.sum(Inventory.quantity_on_hand), 0))
            .group_by(Inventory.product_id)
        ).all())

        d = max(0.0, min(discount_pct, 90.0)) / 100.0
        per_product, base_rev = [], 0.0
        tot_rev = tot_margin = base_margin = tot_units = base_units = 0.0
        earliest_stockout, stockout_product = None, None

        for product, cat_name in targets:
            elasticity, source = self._estimate_elasticity(db, product.id, cat_name)
            v = velocity.get(product.id, 0.0)
            price, cost = _f(product.price), _f(product.cost)
            new_price = price * (1 - d)

            uplift = max(-0.9, elasticity * -d)          # -d price change -> demand response
            new_v = v * (1 + uplift)
            on_hand = int(stock.get(product.id, 0))

            b_units = v * duration_days
            n_units = new_v * duration_days
            b_rev, n_rev = b_units * price, n_units * new_price
            b_marg = b_units * (price - cost)
            n_marg = n_units * (new_price - cost)

            days_to_stockout = int(on_hand / new_v) if new_v > 0 else None
            if days_to_stockout is not None and days_to_stockout <= duration_days:
                if earliest_stockout is None or days_to_stockout < earliest_stockout:
                    earliest_stockout, stockout_product = days_to_stockout, product.name

            base_rev += b_rev; tot_rev += n_rev
            base_margin += b_marg; tot_margin += n_marg
            base_units += b_units; tot_units += n_units

            per_product.append({
                "sku": product.sku, "name": product.name, "category": cat_name,
                "elasticity": elasticity, "elasticity_source": source,
                "list_price": round(price, 2), "promo_price": round(new_price, 2),
                "baseline_units": round(b_units, 1), "projected_units": round(n_units, 1),
                "unit_uplift_pct": round(uplift * 100, 1),
                "baseline_revenue": round(b_rev, 2), "projected_revenue": round(n_rev, 2),
                "projected_margin": round(n_marg, 2),
                "on_hand": on_hand, "days_to_stockout": days_to_stockout,
            })

        tot_margin -= extra_spend
        rev_change = ((tot_rev - base_rev) / base_rev * 100) if base_rev else 0.0
        marg_change = ((tot_margin - base_margin) / base_margin * 100) if base_margin else 0.0
        unit_change = ((tot_units - base_units) / base_units * 100) if base_units else 0.0

        results = {
            "sales": {"value": f"{unit_change:+.0f}%", "change": round(unit_change, 1),
                      "positive": unit_change >= 0},
            "revenue": {"value": f"{rev_change:+.0f}%", "change": round(rev_change, 1),
                        "positive": rev_change >= 0},
            "profit": {"value": f"{marg_change:+.0f}%", "change": round(marg_change, 1),
                       "positive": marg_change >= 0},
            "inventory": {
                "value": (f"Stockout in {earliest_stockout} days" if earliest_stockout is not None
                          else "Stock holds"),
                "change": -(earliest_stockout or 0),
                "positive": earliest_stockout is None,
                "isStockout": earliest_stockout is not None,
            },
            "totals": {
                "baseline_revenue": round(base_rev, 2), "projected_revenue": round(tot_rev, 2),
                "baseline_margin": round(base_margin, 2), "projected_margin": round(tot_margin, 2),
                "baseline_units": round(base_units, 1), "projected_units": round(tot_units, 1),
                "extra_spend": extra_spend,
            },
            "products": sorted(per_product, key=lambda p: -p["projected_revenue"])[:10],
        }

        verdict = "recommended" if (rev_change > 0 and marg_change > -10) else "not recommended"
        summary = (
            f"A {discount_pct:.0f}% discount across {len(targets)} product(s) for {duration_days} "
            f"days is projected to lift units {unit_change:+.0f}% and revenue {rev_change:+.0f}%, "
            f"with margin {marg_change:+.0f}%"
            + (f". {stockout_product} would stock out in {earliest_stockout} days, so reorder before launch."
               if earliest_stockout is not None else ".")
            + f" Campaign is {verdict}."
        )
        results["verdict"] = verdict

        record = None
        if persist:
            count = db.scalar(select(func.count()).select_from(Simulation)) or 0
            record = Simulation(
                code=f"SIM-{count + 1:04d}", name=name,
                scenario={"discount_pct": discount_pct, "duration_days": duration_days,
                          "product_skus": product_skus, "category": category,
                          "extra_spend": extra_spend},
                results=results, summary=summary, created_by_id=user_id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return {
            "id": record.id if record else None,
            "code": record.code if record else None,
            "name": name, "summary": summary, "results": results, "recommendation": summary,
        }


simulation_service = SimulationService()
