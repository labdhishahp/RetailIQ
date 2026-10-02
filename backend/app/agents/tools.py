"""The tool surface available to copilot agents.

Every tool executes a real query against the operational database. Agents have
no other data access, so an investigation's findings are always traceable to
rows that exist.

Each tool is published with a JSON schema (TOOL_SPECS) so a model can choose
tools and arguments itself; call_tool validates arguments against the same
schema, so the rule-based and model-driven agents go through one gate.
"""

from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Campaign, Category, Customer, Inventory, Product, Sale, SaleItem, Store,
)
from app.services.analytics_service import _f, _pct_change, analytics_service
from app.services.rag_service import rag_service


class ToolError(ValueError):
    """A tool was called with arguments its schema does not allow."""


def _anchor(db: Session):
    return analytics_service._now(db)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(int(value), high))


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------

def sales_summary(db: Session, *, days: int = 90) -> dict:
    """Revenue, profit and order totals for the window vs the preceding one."""
    days = _clamp(days, 7, 365)
    now = _anchor(db)
    cur = analytics_service._revenue_profit_orders(db, now - timedelta(days=days), now)
    prev = analytics_service._revenue_profit_orders(
        db, now - timedelta(days=days * 2), now - timedelta(days=days))
    return {
        "window_days": days,
        "revenue": round(cur[0], 2), "profit": round(cur[1], 2), "orders": cur[2],
        "revenue_change_pct": _pct_change(cur[0], prev[0]),
        "profit_change_pct": _pct_change(cur[1], prev[1]),
        "orders_change_pct": _pct_change(cur[2], prev[2]),
    }


def product_sales_trend(db: Session, *, name_contains: str = "", days: int = 90) -> list[dict]:
    """Per-product units, revenue and period-over-period change, worst first."""
    days = _clamp(days, 7, 365)
    now = _anchor(db)
    recent, prior = now - timedelta(days=days), now - timedelta(days=days * 2)
    q = (
        select(
            Product.sku, Product.name, Category.name.label("category"),
            func.coalesce(func.sum(case((Sale.sale_date >= recent, SaleItem.quantity), else_=0)), 0),
            func.coalesce(func.sum(case((Sale.sale_date >= recent, SaleItem.line_total), else_=0)), 0),
            func.coalesce(func.sum(case((Sale.sale_date.between(prior, recent), SaleItem.line_total), else_=0)), 0),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .join(Category, Category.id == Product.category_id)
        .where(Sale.sale_date >= prior)
        .group_by(Product.sku, Product.name, Category.name)
    )
    if name_contains:
        q = q.where(Product.name.ilike(f"%{name_contains}%"))
    rows = db.execute(q).all()
    out = [
        {"sku": r[0], "name": r[1], "category": r[2], "units": int(r[3] or 0),
         "revenue": round(_f(r[4]), 2), "prior_revenue": round(_f(r[5]), 2),
         "change_pct": _pct_change(_f(r[4]), _f(r[5]))}
        for r in rows
    ]
    return sorted(out, key=lambda r: r["change_pct"])[:15]


def category_performance(db: Session) -> list[dict]:
    """Revenue share and momentum by category."""
    now = _anchor(db)
    recent, prior = now - timedelta(days=90), now - timedelta(days=180)
    rows = db.execute(
        select(
            Category.name,
            func.coalesce(func.sum(case((Sale.sale_date >= recent, SaleItem.line_total), else_=0)), 0),
            func.coalesce(func.sum(case((Sale.sale_date.between(prior, recent), SaleItem.line_total), else_=0)), 0),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .join(Category, Category.id == Product.category_id)
        .group_by(Category.name)
    ).all()
    total = sum(_f(r[1]) for r in rows) or 1
    return sorted(
        [{"category": r[0], "revenue": round(_f(r[1]), 2),
          "share_pct": round(_f(r[1]) / total * 100, 1),
          "change_pct": _pct_change(_f(r[1]), _f(r[2]))} for r in rows],
        key=lambda r: r["change_pct"],
    )


def product_drilldown(db: Session, *, sku: str) -> dict:
    """One product in depth: weekly units and price, per-store sales and stock.

    This is the tool an agent reaches for once a broad tool has surfaced a
    product worth explaining: it separates a demand problem (units falling at
    a steady price), a price effect (realised price moving), a supply problem
    (stock near zero where it sells) and a location problem (one store).
    """
    product = db.scalar(select(Product).where(Product.sku == sku))
    if product is None:
        return {"found": False, "sku": sku}

    now = _anchor(db)
    week = func.date_trunc("week", Sale.sale_date).label("wk")
    weekly_rows = db.execute(
        select(week, func.sum(SaleItem.quantity), func.sum(SaleItem.line_total))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(SaleItem.product_id == product.id, Sale.sale_date >= now - timedelta(weeks=12))
        .group_by(week).order_by(week)
    ).all()
    weekly = []
    for wk, units, revenue in weekly_rows:
        units, revenue = int(units or 0), _f(revenue)
        weekly.append({"week": wk.date().isoformat(), "units": units, "revenue": round(revenue, 2),
                       "avg_price": round(revenue / units, 2) if units else 0.0})

    def window(rows):
        units = sum(w["units"] for w in rows)
        revenue = sum(w["revenue"] for w in rows)
        return units, (revenue / units if units else 0.0)

    last4_units, last4_price = window(weekly[-4:])
    prev4_units, prev4_price = window(weekly[-8:-4])

    recent, prior = now - timedelta(days=90), now - timedelta(days=180)
    store_rows = db.execute(
        select(Store.name,
               func.coalesce(func.sum(case((Sale.sale_date >= recent, SaleItem.line_total), else_=0)), 0),
               func.coalesce(func.sum(case((Sale.sale_date < recent, SaleItem.line_total), else_=0)), 0))
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Store, Store.id == Sale.store_id)
        .where(SaleItem.product_id == product.id, Sale.sale_date >= prior)
        .group_by(Store.name)
    ).all()
    stock = dict(db.execute(
        select(Store.name, Inventory.quantity_on_hand)
        .join(Store, Store.id == Inventory.store_id)
        .where(Inventory.product_id == product.id)
    ).all())

    by_store = [
        {"store": name, "revenue_90d": round(_f(cur), 2), "prior_revenue_90d": round(_f(prev), 2),
         "change_pct": _pct_change(_f(cur), _f(prev)),
         "revenue_lost": round(max(_f(prev) - _f(cur), 0.0), 2),
         "on_hand": int(stock.get(name, 0))}
        for name, cur, prev in store_rows
    ]
    seen = {s["store"] for s in by_store}
    by_store += [{"store": name, "revenue_90d": 0.0, "prior_revenue_90d": 0.0, "change_pct": 0.0,
                  "revenue_lost": 0.0, "on_hand": int(qty)}
                 for name, qty in stock.items() if name not in seen]
    by_store.sort(key=lambda s: s["change_pct"])

    category = db.get(Category, product.category_id)
    return {
        "found": True, "sku": product.sku, "name": product.name,
        "category": category.name if category else None, "status": product.status,
        "list_price": _f(product.price), "unit_cost": _f(product.cost),
        "weekly": weekly,
        "units_last_4w": last4_units, "units_prior_4w": prev4_units,
        "units_change_pct": _pct_change(last4_units, prev4_units),
        "avg_price_last_4w": round(last4_price, 2), "avg_price_prior_4w": round(prev4_price, 2),
        "price_change_pct": _pct_change(last4_price, prev4_price) if prev4_price else 0.0,
        "on_hand_total": int(sum(stock.values())),
        "by_store": by_store,
    }


def inventory_status(db: Session, *, name_contains: str = "") -> list[dict]:
    """Stock position per product with reorder pressure and cover in days."""
    velocity = analytics_service._daily_velocity(db)
    q = (
        select(
            Product.id, Product.sku, Product.name,
            func.sum(Inventory.quantity_on_hand), func.sum(Inventory.reorder_level),
            func.sum(Inventory.reorder_quantity), Product.cost,
        )
        .select_from(Inventory)
        .join(Product, Product.id == Inventory.product_id)
        .group_by(Product.id, Product.sku, Product.name, Product.cost)
    )
    if name_contains:
        q = q.where(Product.name.ilike(f"%{name_contains}%"))
    out = []
    for pid, sku, name, qty, lvl, rq, cost in db.execute(q).all():
        qty, lvl = int(qty or 0), int(lvl or 0)
        v = velocity.get(pid, 0.0)
        out.append({
            "sku": sku, "name": name, "on_hand": qty, "reorder_level": lvl,
            "reorder_quantity": int(rq or 0),
            "daily_velocity": round(v, 2),
            "days_cover": int(qty / v) if v > 0 else None,
            "stock_value": round(qty * _f(cost), 2),
            "below_reorder": qty <= lvl,
        })
    return sorted(out, key=lambda r: (r["days_cover"] is None, r["days_cover"] or 0))[:15]


def pricing_position(db: Session, *, name_contains: str = "") -> list[dict]:
    """Price, cost and 90-day realised margin — flags discounting against list price."""
    now = _anchor(db)
    # The 90-day window has to filter the sale lines themselves; a date
    # condition on an outer join to Sale would still count every line.
    recent = (
        select(SaleItem.product_id,
               func.avg(SaleItem.unit_price).label("avg_price"),
               func.sum(SaleItem.quantity).label("units"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.sale_date >= now - timedelta(days=90))
        .group_by(SaleItem.product_id)
        .subquery()
    )
    q = (
        select(Product.sku, Product.name, Product.price, Product.cost,
               func.coalesce(recent.c.avg_price, 0), func.coalesce(recent.c.units, 0))
        .outerjoin(recent, recent.c.product_id == Product.id)
    )
    if name_contains:
        q = q.where(Product.name.ilike(f"%{name_contains}%"))
    out = []
    for sku, name, price, cost, avg_price, units in db.execute(q).all():
        p, c, a = _f(price), _f(cost), _f(avg_price)
        out.append({
            "sku": sku, "name": name, "list_price": p, "unit_cost": c,
            "avg_selling_price": round(a, 2),
            "list_margin_pct": round((p - c) / p * 100, 1) if p else 0.0,
            "realised_margin_pct": round((a - c) / a * 100, 1) if a else 0.0,
            "discount_vs_list_pct": round((p - a) / p * 100, 1) if p and a else 0.0,
            "units_90d": int(units or 0),
        })
    return sorted(out, key=lambda r: -r["discount_vs_list_pct"])[:15]


def campaign_status(db: Session) -> list[dict]:
    """Campaign spend, return and ROI for every campaign."""
    rows = db.scalars(select(Campaign)).all()
    return [{
        "code": c.code, "name": c.name, "channel": c.channel, "status": c.status,
        "budget": _f(c.budget), "spent": _f(c.spent), "revenue": _f(c.revenue),
        "roi": round(_f(c.revenue) / _f(c.spent), 2) if _f(c.spent) else 0.0,
        "conversions": c.conversions,
    } for c in rows]


def customer_health(db: Session) -> dict:
    """Segment mix, churn exposure and the most valuable lapsing customers."""
    lapsing = Customer.status.in_(["at_risk", "churned"])
    rows = db.execute(
        select(Customer.segment, func.count(), func.coalesce(func.sum(Customer.total_spent), 0))
        .group_by(Customer.segment)
    ).all()
    at_risk = db.execute(
        select(Customer.code, Customer.name, Customer.total_spent, Customer.last_order_date)
        .where(lapsing).order_by(Customer.total_spent.desc()).limit(8)
    ).all()
    # Totals come from their own aggregate: the list above is only the top 8.
    count, spend = db.execute(
        select(func.count(), func.coalesce(func.sum(Customer.total_spent), 0)).where(lapsing)
    ).one()
    total_spend = sum(_f(r[2]) for r in rows) or 1
    return {
        "segments": [{"segment": r[0], "customers": int(r[1]),
                      "spend": round(_f(r[2]), 2),
                      "spend_share_pct": round(_f(r[2]) / total_spend * 100, 1)} for r in rows],
        "at_risk": [{"code": r[0], "name": r[1], "spend": round(_f(r[2]), 2),
                     "last_order": str(r[3]) if r[3] else None} for r in at_risk],
        "at_risk_count": int(count or 0),
        "at_risk_spend": round(_f(spend), 2),
    }


def store_performance(db: Session) -> list[dict]:
    """Revenue, orders and growth per store over 90 days vs the prior 90."""
    return analytics_service.store_comparison(db)


def search_knowledge_base(db: Session, *, query: str, limit: int = 4) -> list[dict]:
    """Retrieve policy and context passages from the document corpus (hybrid RAG)."""
    hits = rag_service.search(db, query, limit=_clamp(limit, 1, 8))
    return [{"title": h["title"], "doc_type": h["doc_type"],
             "excerpt": h["content"][:400], "document_id": h["document_id"],
             "chunk_id": h["chunk_id"], "similarity": h["similarity"]} for h in hits]


# --------------------------------------------------------------------------
# Registry and schemas
# --------------------------------------------------------------------------

TOOLS = {
    "sales_summary": sales_summary,
    "product_sales_trend": product_sales_trend,
    "category_performance": category_performance,
    "product_drilldown": product_drilldown,
    "inventory_status": inventory_status,
    "pricing_position": pricing_position,
    "campaign_status": campaign_status,
    "customer_health": customer_health,
    "store_performance": store_performance,
    "search_knowledge_base": search_knowledge_base,
}

_NAME = {"type": "string",
         "description": "Case-insensitive substring of a product name; empty string for all products."}
_DAYS = {"type": "integer", "description": "Window length in days (7-365). 90 is the house default."}

# Strict schemas: every property is required (an empty string means "no
# filter"), so a model can never send an argument the function does not take.
_PARAMS: dict[str, dict] = {
    "sales_summary": {"days": _DAYS},
    "product_sales_trend": {
        "name_contains": _NAME,
        "days": _DAYS,
    },
    "category_performance": {},
    "product_drilldown": {
        "sku": {"type": "string", "description": "Product SKU, taken from another tool's output."},
    },
    "inventory_status": {"name_contains": _NAME},
    "pricing_position": {"name_contains": _NAME},
    "campaign_status": {},
    "customer_health": {},
    "store_performance": {},
    "search_knowledge_base": {
        "query": {"type": "string", "description": "Natural-language search over policies and playbooks."},
        "limit": {"type": "integer", "description": "Passages to return (1-8)."},
    },
}

_GUIDANCE = {
    "product_sales_trend": " Use it to find which products drive a revenue change.",
    "product_drilldown": (" Use it after another tool surfaces a product, to tell a demand, "
                          "price, stock or single-store cause apart."),
    "inventory_status": " Sorted by fewest days of cover first.",
    "pricing_position": " Sorted by deepest discount first.",
}

TOOL_DESCRIPTIONS = {
    name: (fn.__doc__ or "").strip().split("\n")[0] for name, fn in TOOLS.items()
}

TOOL_SPECS: dict[str, dict] = {
    name: {
        "name": name,
        "description": TOOL_DESCRIPTIONS[name] + _GUIDANCE.get(name, ""),
        "input_schema": {
            "type": "object",
            "properties": params,
            "required": list(params),
            "additionalProperties": False,
        },
        "strict": True,
    }
    for name, params in _PARAMS.items()
}


def _validate(name: str, kwargs: dict) -> dict:
    props = _PARAMS[name]
    unknown = set(kwargs) - set(props)
    if unknown:
        raise ToolError(f"{name} does not accept: {', '.join(sorted(unknown))}")
    clean = {}
    for key, value in kwargs.items():
        expected = props[key]["type"]
        if expected == "integer":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ToolError(f"{name}.{key} must be an integer")
            value = int(value)
        elif expected == "string" and not isinstance(value, str):
            raise ToolError(f"{name}.{key} must be a string")
        clean[key] = value
    return clean


def call_tool(db: Session, name: str, **kwargs):
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    return TOOLS[name](db, **_validate(name, kwargs))
