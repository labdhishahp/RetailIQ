"""The tool surface available to copilot agents.

Every tool executes a real query against the operational database. Agents have
no other data access, so an investigation's findings are always traceable to
rows that exist.
"""

from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Campaign, Category, Customer, Inventory, Product, Sale, SaleItem, Store,
)
from app.services.analytics_service import _f, _pct_change, analytics_service
from app.services.rag_service import rag_service


def _anchor(db: Session):
    return analytics_service._now(db)


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------

def sales_summary(db: Session, *, days: int = 90) -> dict:
    """Revenue, profit and order totals for the window vs the preceding one."""
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
    """Per-product units, revenue and period-over-period change."""
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


def inventory_status(db: Session, *, name_contains: str = "") -> list[dict]:
    """Stock position per product with reorder pressure and cover in days."""
    now = _anchor(db)
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
    """Price, cost and realised margin — flags discounting against list price."""
    now = _anchor(db)
    q = (
        select(
            Product.sku, Product.name, Product.price, Product.cost,
            func.coalesce(func.avg(SaleItem.unit_price), 0),
            func.coalesce(func.sum(SaleItem.quantity), 0),
        )
        .select_from(Product)
        .outerjoin(SaleItem, SaleItem.product_id == Product.id)
        .outerjoin(Sale, (Sale.id == SaleItem.sale_id) & (Sale.sale_date >= now - timedelta(days=90)))
        .group_by(Product.sku, Product.name, Product.price, Product.cost)
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
    """Live campaign spend and return."""
    rows = db.scalars(select(Campaign)).all()
    return [{
        "code": c.code, "name": c.name, "channel": c.channel, "status": c.status,
        "budget": _f(c.budget), "spent": _f(c.spent), "revenue": _f(c.revenue),
        "roi": round(_f(c.revenue) / _f(c.spent), 2) if _f(c.spent) else 0.0,
        "conversions": c.conversions,
    } for c in rows]


def customer_health(db: Session) -> dict:
    """Segment mix, churn exposure and concentration."""
    now = _anchor(db)
    rows = db.execute(
        select(Customer.segment, func.count(), func.coalesce(func.sum(Customer.total_spent), 0))
        .group_by(Customer.segment)
    ).all()
    at_risk = db.execute(
        select(Customer.code, Customer.name, Customer.total_spent, Customer.last_order_date)
        .where(Customer.status.in_(["at_risk", "churned"]))
        .order_by(Customer.total_spent.desc()).limit(8)
    ).all()
    total_spend = sum(_f(r[2]) for r in rows) or 1
    return {
        "segments": [{"segment": r[0], "customers": int(r[1]),
                      "spend": round(_f(r[2]), 2),
                      "spend_share_pct": round(_f(r[2]) / total_spend * 100, 1)} for r in rows],
        "at_risk": [{"code": r[0], "name": r[1], "spend": round(_f(r[2]), 2),
                     "last_order": str(r[3]) if r[3] else None} for r in at_risk],
        "at_risk_count": len(at_risk),
    }


def store_performance(db: Session) -> list[dict]:
    """Revenue and growth per store."""
    return analytics_service.store_comparison(db)


def search_knowledge_base(db: Session, *, query: str, limit: int = 4) -> list[dict]:
    """Retrieve supporting passages from the document corpus (RAG)."""
    hits = rag_service.search(db, query, limit=limit)
    return [{"title": h["title"], "doc_type": h["doc_type"],
             "excerpt": h["content"][:400], "document_id": h["document_id"],
             "chunk_id": h["chunk_id"], "similarity": h["similarity"]} for h in hits]


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

TOOLS = {
    "sales_summary": sales_summary,
    "product_sales_trend": product_sales_trend,
    "category_performance": category_performance,
    "inventory_status": inventory_status,
    "pricing_position": pricing_position,
    "campaign_status": campaign_status,
    "customer_health": customer_health,
    "store_performance": store_performance,
    "search_knowledge_base": search_knowledge_base,
}

TOOL_DESCRIPTIONS = {
    name: (fn.__doc__ or "").strip().split("\n")[0] for name, fn in TOOLS.items()
}


def call_tool(db: Session, name: str, **kwargs):
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    return TOOLS[name](db, **kwargs)
