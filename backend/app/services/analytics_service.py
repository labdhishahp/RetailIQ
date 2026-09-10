"""Aggregate analytics computed in SQL from the operational tables.

Every figure returned here is derived from real rows in stores / products /
categories / inventory / sales / sale_items. Where the schema cannot supply a
metric directly (there is no stock-history or fulfilment table), the derivation
used is documented on the method that computes it.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session

from app.models import Campaign, Category, Inventory, Product, Sale, SaleItem, Store

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _f(value) -> float:
    """Decimal/None -> float."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return round((current - previous) / previous * 100, 1)


def _trend(change: float) -> str:
    return "up" if change >= 0 else "down"


class AnalyticsService:
    """Read-only aggregate queries backing the dashboard and analytics pages."""

    # ---------- helpers -------------------------------------------------

    def _now(self, db: Session) -> datetime:
        """Anchor analytics to the newest sale so seeded data always renders."""
        latest = db.scalar(select(func.max(Sale.sale_date)))
        return latest or datetime.now(timezone.utc)

    def _revenue_profit_orders(self, db: Session, start: datetime, end: datetime):
        row = db.execute(
            select(
                func.coalesce(func.sum(SaleItem.line_total), 0),
                func.coalesce(
                    func.sum(SaleItem.line_total - SaleItem.unit_cost * SaleItem.quantity), 0
                ),
                func.count(func.distinct(Sale.id)),
            )
            .select_from(Sale)
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .where(Sale.sale_date >= start, Sale.sale_date < end)
        ).one()
        return _f(row[0]), _f(row[1]), int(row[2] or 0)

    # ---------- KPIs ----------------------------------------------------

    def kpis(self, db: Session) -> dict:
        """Trailing 30 days vs the 30 days before that.

        healthScore is a composite of three real signals, equally weighted:
        margin ratio, inventory fill rate, and order-growth momentum. The
        formula is defined here because the schema has no health column.
        """
        now = self._now(db)
        cur_start, prev_start = now - timedelta(days=30), now - timedelta(days=60)

        revenue, profit, orders = self._revenue_profit_orders(db, cur_start, now)
        p_revenue, p_profit, p_orders = self._revenue_profit_orders(db, prev_start, cur_start)

        margin_ratio = (profit / revenue) if revenue else 0.0
        fill = self._fill_rate(db) / 100
        growth = _pct_change(orders, p_orders)
        momentum = max(0.0, min(1.0, (growth + 20) / 40))
        health = round((margin_ratio + fill + momentum) / 3 * 100, 1)

        prev_margin = (p_profit / p_revenue) if p_revenue else 0.0
        prev_momentum = max(0.0, min(1.0, (_pct_change(p_orders, orders) + 20) / 40))
        prev_health = round((prev_margin + fill + prev_momentum) / 3 * 100, 1)

        def metric(v, pv):
            c = _pct_change(v, pv)
            return {"value": round(v, 2), "change": c, "trend": _trend(c)}

        return {
            "revenue": metric(revenue, p_revenue),
            "orders": metric(orders, p_orders),
            "profit": metric(profit, p_profit),
            "healthScore": metric(health, prev_health),
        }

    # ---------- time series ---------------------------------------------

    def revenue_trend(self, db: Session, months: int = 12) -> list[dict]:
        now = self._now(db)
        # step back exactly `months - 1` calendar months, then to the 1st,
        # so the series is always N buckets rather than N+1 partial ones
        year, month = now.year, now.month - (months - 1)
        while month <= 0:
            month += 12
            year -= 1
        start = now.replace(year=year, month=month, day=1, hour=0, minute=0,
                            second=0, microsecond=0)
        bucket = func.date_trunc("month", Sale.sale_date).label("bucket")

        rows = db.execute(
            select(
                bucket,
                func.coalesce(func.sum(SaleItem.line_total), 0),
                func.coalesce(
                    func.sum(SaleItem.line_total - SaleItem.unit_cost * SaleItem.quantity), 0
                ),
                func.count(func.distinct(Sale.id)),
            )
            .select_from(Sale)
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .where(Sale.sale_date >= start)
            .group_by(bucket)
            .order_by(bucket)
        ).all()

        return [
            {
                "month": MONTH_LABELS[r[0].month - 1],
                "revenue": round(_f(r[1]), 2),
                "profit": round(_f(r[2]), 2),
                "orders": int(r[3] or 0),
            }
            for r in rows
        ][-months:]

    def monthly_sales(self, db: Session, months: int = 12) -> list[dict]:
        return [
            {"month": p["month"], "sales": p["orders"]}
            for p in self.revenue_trend(db, months)
        ]

    def sales_by_period(self, db: Session, period: str) -> list[dict]:
        """period: 'daily' (last 7 days) | 'weekly' (last 8 weeks) | 'monthly'."""
        now = self._now(db)
        if period == "monthly":
            pts = self.revenue_trend(db, 12)
            out = []
            for i, p in enumerate(pts):
                prev = pts[i - 1]["revenue"] if i else p["revenue"]
                out.append({
                    "label": p["month"], "revenue": p["revenue"], "profit": p["profit"],
                    "orders": p["orders"], "growth": _pct_change(p["revenue"], prev),
                })
            return out

        if period == "weekly":
            trunc, span, fmt = "week", timedelta(weeks=8), "W"
        else:
            trunc, span, fmt = "day", timedelta(days=7), "D"

        bucket = func.date_trunc(trunc, Sale.sale_date).label("bucket")
        rows = db.execute(
            select(
                bucket,
                func.coalesce(func.sum(SaleItem.line_total), 0),
                func.coalesce(
                    func.sum(SaleItem.line_total - SaleItem.unit_cost * SaleItem.quantity), 0
                ),
                func.count(func.distinct(Sale.id)),
            )
            .select_from(Sale)
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .where(Sale.sale_date >= now - span)
            .group_by(bucket)
            .order_by(bucket)
        ).all()

        out = []
        for i, r in enumerate(rows):
            revenue = round(_f(r[1]), 2)
            prev = out[-1]["revenue"] if out else revenue
            label = r[0].strftime("%a") if fmt == "D" else f"W{i + 1}"
            out.append({
                "label": label, "revenue": revenue, "profit": round(_f(r[2]), 2),
                "orders": int(r[3] or 0), "growth": _pct_change(revenue, prev),
            })
        return out

    # ---------- breakdowns ------------------------------------------------

    def store_comparison(self, db: Session) -> list[dict]:
        now = self._now(db)
        recent, prior = now - timedelta(days=90), now - timedelta(days=180)

        def window(start, end):
            rows = db.execute(
                select(Store.name,
                       func.coalesce(func.sum(SaleItem.line_total), 0),
                       func.count(func.distinct(Sale.id)))
                .select_from(Sale)
                .join(Store, Store.id == Sale.store_id)
                .join(SaleItem, SaleItem.sale_id == Sale.id)
                .where(Sale.sale_date >= start, Sale.sale_date < end)
                .group_by(Store.name)
            ).all()
            return {r[0]: (_f(r[1]), int(r[2] or 0)) for r in rows}

        cur, prev = window(recent, now), window(prior, recent)
        out = []
        for name, (revenue, orders) in sorted(cur.items(), key=lambda kv: -kv[1][0]):
            out.append({
                "store": name, "revenue": round(revenue, 2), "orders": orders,
                "growth": _pct_change(revenue, prev.get(name, (0.0, 0))[0]),
            })
        return out

    def category_sales(self, db: Session) -> list[dict]:
        rows = db.execute(
            select(Category.name, func.coalesce(func.sum(SaleItem.line_total), 0))
            .select_from(SaleItem)
            .join(Product, Product.id == SaleItem.product_id)
            .join(Category, Category.id == Product.category_id)
            .group_by(Category.name)
            .order_by(func.sum(SaleItem.line_total).desc())
        ).all()
        total = sum(_f(r[1]) for r in rows) or 1.0
        return [
            {"category": r[0], "value": round(_f(r[1]) / total * 100, 1),
             "revenue": round(_f(r[1]), 2)}
            for r in rows
        ]

    def top_products(self, db: Session, limit: int = 5) -> list[dict]:
        now = self._now(db)
        recent, prior = now - timedelta(days=90), now - timedelta(days=180)

        stock_sub = (
            select(Inventory.product_id,
                   func.coalesce(func.sum(Inventory.quantity_on_hand), 0).label("stock"))
            .group_by(Inventory.product_id).subquery()
        )

        rows = db.execute(
            select(
                Product.id, Product.name, Category.name,
                func.coalesce(func.sum(
                    case((Sale.sale_date >= recent, SaleItem.quantity), else_=0)), 0),
                func.coalesce(func.sum(
                    case((Sale.sale_date >= recent, SaleItem.line_total), else_=0)), 0),
                func.coalesce(func.sum(
                    case((Sale.sale_date.between(prior, recent), SaleItem.line_total),
                         else_=0)), 0),
                func.coalesce(stock_sub.c.stock, 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(stock_sub, stock_sub.c.product_id == Product.id)
            .group_by(Product.id, Product.name, Category.name, stock_sub.c.stock)
            .order_by(func.sum(
                case((Sale.sale_date >= recent, SaleItem.line_total), else_=0)).desc())
            .limit(limit)
        ).all()

        return [
            {"id": r[0], "name": r[1], "category": r[2], "sales": int(r[3] or 0),
             "revenue": round(_f(r[4]), 2), "growth": _pct_change(_f(r[4]), _f(r[5])),
             "stock": int(r[6] or 0)}
            for r in rows
        ]

    # ---------- product overview -----------------------------------------

    def products_overview(self, db: Session) -> list[dict]:
        """Products joined to cross-store stock, with margin computed in SQL."""
        stock_sub = (
            select(Inventory.product_id,
                   func.coalesce(func.sum(Inventory.quantity_on_hand), 0).label("stock"))
            .group_by(Inventory.product_id).subquery()
        )
        rows = db.execute(
            select(Product.sku, Product.name, Category.name, Product.supplier,
                   Product.price, Product.cost, Product.status,
                   func.coalesce(stock_sub.c.stock, 0))
            .join(Category, Category.id == Product.category_id)
            .outerjoin(stock_sub, stock_sub.c.product_id == Product.id)
            .order_by(Product.sku)
        ).all()

        out = []
        for sku, name, cat, supplier, price, cost, status, stock in rows:
            p, c = _f(price), _f(cost)
            out.append({
                "id": sku, "name": name, "category": cat, "supplier": supplier,
                "price": p, "cost": c, "stock": int(stock or 0), "status": status,
                "margin": round((p - c) / p * 100, 1) if p else 0.0,
            })
        return out

    # ---------- inventory --------------------------------------------------

    def _fill_rate(self, db: Session) -> float:
        row = db.execute(
            select(func.count(), func.coalesce(func.sum(
                case((Inventory.quantity_on_hand > Inventory.reorder_level, 1), else_=0)), 0))
            .select_from(Inventory)
        ).one()
        total = int(row[0] or 0)
        return round(int(row[1] or 0) / total * 100, 1) if total else 0.0

    def _daily_velocity(self, db: Session, days: int = 90) -> dict[int, float]:
        now = self._now(db)
        rows = db.execute(
            select(SaleItem.product_id, func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.sale_date >= now - timedelta(days=days))
            .group_by(SaleItem.product_id)
        ).all()
        return {int(r[0]): (int(r[1] or 0) / days) for r in rows}

    def inventory_overview(self, db: Session) -> dict:
        now = self._now(db)
        velocity = self._daily_velocity(db)

        detail_rows = db.execute(
            select(Product.id, Product.sku, Product.name, Product.cost,
                   Inventory.quantity_on_hand, Inventory.reorder_level,
                   Inventory.reorder_quantity, Inventory.warehouse_name,
                   Category.name, Store.name, Store.id)
            .select_from(Inventory)
            .join(Product, Product.id == Inventory.product_id)
            .join(Category, Category.id == Product.category_id)
            .join(Store, Store.id == Inventory.store_id)
        ).all()

        inv_by_product: dict[int, list[int]] = {}
        by_product: dict[int, dict] = {}
        warehouses: dict[str, dict] = {}
        for pid, sku, name, cost, qty, lvl, rq, wh, cat, _store, _sid in detail_rows:
            inv_by_product.setdefault(pid, []).append(pid)
            qty, lvl, rq, cost = int(qty or 0), int(lvl or 0), int(rq or 0), _f(cost)
            agg = by_product.setdefault(pid, {
                "sku": sku, "name": name, "cost": cost, "qty": 0,
                "reorder": 0, "reorder_qty": 0, "category": cat})
            agg["qty"] += qty
            agg["reorder"] += lvl
            agg["reorder_qty"] += rq
            w = warehouses.setdefault(wh or "Unassigned",
                                      {"skus": 0, "value": 0.0, "qty": 0, "cap": 0})
            w["skus"] += 1
            w["value"] += qty * cost
            w["qty"] += qty
            w["cap"] += lvl + rq

        total_value = sum(a["qty"] * a["cost"] for a in by_product.values())
        total_skus = db.scalar(select(func.count()).select_from(Product)) or 0

        sold_year = db.scalar(
            select(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.sale_date >= now - timedelta(days=365))) or 0
        avg_stock = sum(a["qty"] for a in by_product.values()) or 1
        turnover = round(int(sold_year) / avg_stock, 1)

        # Shortages and excess are evaluated per stocking location: a single
        # store can be out while the chain still holds stock, which is the
        # situation a replenishment view needs to surface.
        low, dead, over, reorder = [], [], [], []
        for pid, sku, name, cost, qty, lvl, rq, wh, cat, store_name, store_id in detail_rows:
            qty, lvl, rq, cost = int(qty or 0), int(lvl or 0), int(rq or 0), _f(cost)
            v = velocity.get(pid, 0.0) / max(len(inv_by_product.get(pid, [1])), 1)
            if lvl and qty <= lvl:
                days_left = int(qty / v) if v > 0 else 99
                low.append({"id": sku, "name": f"{name} · {store_name}", "current": qty,
                            "reorder": lvl, "daysLeft": min(days_left, 99),
                            "product_id": pid, "store_id": store_id, "store": store_name})
                ratio = qty / lvl if lvl else 1
                reorder.append({
                    "id": sku, "name": f"{name} · {store_name}", "qty": rq,
                    "cost": round(rq * cost, 2),
                    "urgency": "critical" if ratio < 0.5 else "medium",
                    "product_id": pid, "store_id": store_id, "store": store_name,
                })
            optimal = lvl * 2
            if optimal and qty > optimal:
                over.append({"id": sku, "name": f"{name} · {store_name}", "current": qty,
                             "optimal": optimal, "excess": qty - optimal})

        # Dead stock: on hand but no sale in the last 60 days.
        last_sold = dict(db.execute(
            select(SaleItem.product_id, func.max(Sale.sale_date))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .group_by(SaleItem.product_id)
        ).all())
        for pid, a in by_product.items():
            if a["qty"] <= 0:
                continue
            last = last_sold.get(pid)
            idle = (now - last).days if last else 365
            if idle >= 60:
                dead.append({"id": a["sku"], "name": a["name"], "daysIdle": idle,
                             "value": round(a["qty"] * a["cost"], 2), "units": a["qty"]})

        low.sort(key=lambda r: r["daysLeft"])
        dead.sort(key=lambda r: -r["daysIdle"])
        over.sort(key=lambda r: -r["excess"])
        reorder.sort(key=lambda r: (r["urgency"] != "critical", -r["cost"]))

        wh_rows = [
            {"name": n, "capacity": round(min(w["qty"] / w["cap"] * 100, 100), 1) if w["cap"] else 0.0,
             "skus": w["skus"], "value": round(w["value"], 2)}
            for n, w in sorted(warehouses.items())
        ]

        return {
            "summary": {
                "totalSKUs": int(total_skus),
                "totalValue": round(total_value, 2),
                "turnoverRate": turnover,
                "fillRate": self._fill_rate(db),
            },
            "lowStock": low[:6],
            "deadStock": dead[:6],
            "overstock": over[:6],
            "reorderSuggestions": reorder[:6],
            "warehouses": wh_rows,
            "heatmap": self._heatmap(db),
        }

    def _heatmap(self, db: Session) -> list[dict]:
        """Weekly stock-health index per category for the last 8 weeks.

        There is no stock-history table for periods before stock_movements
        began, so historical stock is reconstructed by adding units sold after
        each week back onto today's on-hand quantity, then expressed as a
        percentage of that category's peak in the window. Computed in a single
        grouped query rather than one query per week.
        """
        now = self._now(db)
        window_start = now - timedelta(weeks=8)

        cur = dict(db.execute(
            select(Category.name, func.coalesce(func.sum(Inventory.quantity_on_hand), 0))
            .select_from(Inventory)
            .join(Product, Product.id == Inventory.product_id)
            .join(Category, Category.id == Product.category_id)
            .group_by(Category.name)
        ).all())

        # units sold per (category, week) in one pass
        week_bucket = func.date_trunc("week", Sale.sale_date).label("wk")
        rows = db.execute(
            select(Category.name, week_bucket,
                   func.coalesce(func.sum(SaleItem.quantity), 0))
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(Sale.sale_date >= window_start)
            .group_by(Category.name, week_bucket)
        ).all()

        weeks = sorted({r[1] for r in rows})[-8:]
        per: dict[tuple, int] = {(r[0], r[1]): int(r[2] or 0) for r in rows}

        out = []
        for cat, on_hand in sorted(cur.items()):
            # stock at week i = on hand today + everything sold from week i onward
            levels = []
            for i in range(len(weeks)):
                sold_after = sum(per.get((cat, w), 0) for w in weeks[i:])
                levels.append(int(on_hand) + sold_after)
            while len(levels) < 8:
                levels.append(int(on_hand))
            peak = max(levels) or 1
            row = {"category": cat}
            for i, lv in enumerate(levels[:8], start=1):
                row[f"w{i}"] = int(round(lv / peak * 100))
            out.append(row)
        return out

    def inventory_trend(self, db: Session) -> list[dict]:
        """Total stock and turnover per week, reconstructed as in _heatmap.

        One grouped query rather than two per week.
        """
        now = self._now(db)
        on_hand = int(db.scalar(
            select(func.coalesce(func.sum(Inventory.quantity_on_hand), 0))) or 0)

        week_bucket = func.date_trunc("week", Sale.sale_date).label("wk")
        rows = db.execute(
            select(week_bucket, func.coalesce(func.sum(SaleItem.quantity), 0))
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.sale_date >= now - timedelta(weeks=8))
            .group_by(week_bucket).order_by(week_bucket)
        ).all()

        weekly = [(r[0], int(r[1] or 0)) for r in rows][-8:]
        out = []
        for i, (_, sold_this_week) in enumerate(weekly):
            sold_after = sum(q for _, q in weekly[i:])
            stock = on_hand + sold_after
            out.append({
                "week": f"W{i + 1}", "stock": stock,
                "turnover": round(sold_this_week / stock * 52, 1) if stock else 0.0,
            })
        return out

    # ---------- campaigns ---------------------------------------------------

    def campaign_performance(self, db: Session) -> list[dict]:
        rows = db.execute(
            select(Campaign.channel,
                   func.coalesce(func.sum(Campaign.spent), 0),
                   func.coalesce(func.sum(Campaign.revenue), 0))
            .group_by(Campaign.channel)
            .order_by(func.sum(Campaign.revenue).desc())
        ).all()
        return [
            {"channel": r[0], "spend": round(_f(r[1]), 2), "revenue": round(_f(r[2]), 2),
             "roi": round(_f(r[2]) / _f(r[1]), 1) if _f(r[1]) else 0.0}
            for r in rows
        ]


analytics_service = AnalyticsService()
