"""The fixed benchmark: questions, the tools each one requires, and ground truth.

Ground truth is computed from the database at evaluation time with queries
written here, independently of the agent tools, so an agent is never graded
against its own code path. Each definition states its rule exactly; the
expected answer is "the entities (or figure) that rule selects", nothing
subjective. The window conventions match the app's documented analytics:
revenue windows are half-open [start, anchor); sales velocity counts lines
with sale_date >= anchor - 90 days. `anchor` is the newest sale timestamp.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Campaign, Customer, Inventory, Product, Sale, SaleItem, Store


@dataclass(frozen=True)
class Entity:
    key: str          # SKU, campaign code or store name
    name: str


@dataclass
class Truth:
    entities: list[Entity] = field(default_factory=list)
    number: float | None = None       # expected figure, compared by absolute value
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    required_tools: frozenset[str]
    definition: str                   # the ground-truth rule, in words
    truth: Callable[[Session], Truth]


def _anchor(db: Session):
    return db.scalar(select(func.max(Sale.sale_date)))


def _f(value) -> float:
    return float(value or 0)


def _units_90d(db: Session, anchor) -> dict[int, int]:
    rows = db.execute(
        select(SaleItem.product_id, func.sum(SaleItem.quantity))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.sale_date >= anchor - timedelta(days=90))
        .group_by(SaleItem.product_id)
    ).all()
    return {pid: int(units or 0) for pid, units in rows}


def _stock(db: Session) -> list[tuple]:
    return db.execute(
        select(Product.id, Product.sku, Product.name, Product.cost,
               func.sum(Inventory.quantity_on_hand))
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.id, Product.sku, Product.name, Product.cost)
    ).all()


def _revenue(db: Session, start, end, *extra) -> float:
    return _f(db.scalar(
        select(func.coalesce(func.sum(SaleItem.line_total), 0))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.sale_date >= start, Sale.sale_date < end, *extra)))


# ---- ground truth -------------------------------------------------------

def reorder_truth(db: Session) -> Truth:
    anchor = _anchor(db)
    units = _units_90d(db, anchor)
    rows = []
    for pid, sku, name, _cost, on_hand in _stock(db):
        velocity = units.get(pid, 0) / 90
        if velocity > 0 and int(on_hand or 0) / velocity < 21:
            rows.append((int(on_hand or 0) / velocity, sku, name))
    rows.sort()
    return Truth([Entity(sku, name) for _, sku, name in rows[:3]],
                 detail={"qualifying": len(rows)})


def dead_stock_truth(db: Session) -> Truth:
    anchor = _anchor(db)
    units = _units_90d(db, anchor)
    rows = sorted(
        ((int(on_hand or 0) * _f(cost), sku, name)
         for pid, sku, name, cost, on_hand in _stock(db)
         if int(on_hand or 0) > 0 and units.get(pid, 0) == 0),
        reverse=True)
    return Truth([Entity(sku, name) for _, sku, name in rows[:3]],
                 detail={"qualifying": len(rows)})


def shampoo_truth(db: Session) -> Truth:
    anchor = _anchor(db)
    recent, prior = anchor - timedelta(days=90), anchor - timedelta(days=180)
    rows = []
    for pid, sku, name in db.execute(
            select(Product.id, Product.sku, Product.name).where(Product.name.ilike("%shampoo%"))).all():
        cur = _revenue(db, recent, anchor, SaleItem.product_id == pid)
        prev = _revenue(db, prior, recent, SaleItem.product_id == pid)
        if cur < prev:
            rows.append(((cur - prev) / prev if prev else 0.0, sku, name))
    rows.sort()
    return Truth([Entity(sku, name) for _, sku, name in rows[:3]],
                 detail={"qualifying": len(rows)})


def campaign_truth(db: Session) -> Truth:
    rows = sorted(
        (_f(c.revenue) / _f(c.spent), c.code, c.name)
        for c in db.scalars(select(Campaign).where(Campaign.status == "active")).all()
        if _f(c.spent) > 0 and _f(c.revenue) / _f(c.spent) < 2.5)
    return Truth([Entity(code, name) for _, code, name in rows],
                 detail={"qualifying": len(rows)})


def churn_truth(db: Session) -> Truth:
    count = db.scalar(select(func.count()).select_from(Customer)
                      .where(Customer.status.in_(["at_risk", "churned"]))) or 0
    return Truth(number=float(count))


def store_truth(db: Session) -> Truth:
    anchor = _anchor(db)
    recent, prior = anchor - timedelta(days=90), anchor - timedelta(days=180)
    growth = []
    for store_id, name in db.execute(select(Store.id, Store.name)).all():
        cur = _revenue(db, recent, anchor, Sale.store_id == store_id)
        prev = _revenue(db, prior, recent, Sale.store_id == store_id)
        if cur or prev:
            growth.append(((cur - prev) / prev * 100 if prev else 100.0, name))
    if not growth:
        return Truth()
    growth.sort()
    picks = [growth[0]] + ([growth[-1]] if len(growth) > 1 else [])
    return Truth([Entity(name, name) for _, name in picks],
                 detail={"weakest": growth[0][1], "strongest": growth[-1][1]})


def margin_truth(db: Session) -> Truth:
    anchor = _anchor(db)
    rows = db.execute(
        select(Product.sku, Product.name, Product.price, func.avg(SaleItem.unit_price))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.sale_date >= anchor - timedelta(days=90))
        .group_by(Product.sku, Product.name, Product.price)
    ).all()
    discounted = sorted(
        ((-(_f(price) - _f(avg)) / _f(price) * 100, sku, name)
         for sku, name, price, avg in rows
         if _f(price) and (_f(price) - _f(avg)) / _f(price) * 100 > 2))
    return Truth([Entity(sku, name) for _, sku, name in discounted[:3]],
                 detail={"qualifying": len(discounted)})


def revenue_truth(db: Session) -> Truth:
    anchor = _anchor(db)
    cur = _revenue(db, anchor - timedelta(days=90), anchor)
    prev = _revenue(db, anchor - timedelta(days=180), anchor - timedelta(days=90))
    detail = {"revenue_90d": round(cur, 2), "prior_90d": round(prev, 2)}
    if not prev:
        return Truth(detail=detail)   # change is undefined with no prior revenue: not scorable
    return Truth(number=round((cur - prev) / prev * 100, 1), detail=detail)


QUESTIONS: list[Question] = [
    Question("reorder", "Which products need immediate reorder?",
             frozenset({"inventory_status"}),
             "Up to 3 products with the fewest days of cover, where cover = on-hand units / "
             "(units sold in the last 90 days / 90) and cover < 21 days.",
             reorder_truth),
    Question("dead_stock", "Which products are dead stock tying up capital?",
             frozenset({"inventory_status"}),
             "Up to 3 products with stock on hand and no units sold in the last 90 days, "
             "largest stock value (on-hand x cost) first.",
             dead_stock_truth),
    Question("shampoo", "Why are shampoo sales decreasing?",
             frozenset({"product_sales_trend"}),
             "Up to 3 products named like 'shampoo' whose revenue in the last 90 days is below "
             "the prior 90 days, largest relative fall first. Empty if none declined.",
             shampoo_truth),
    Question("campaigns", "Which active campaigns are below their ROI target?",
             frozenset({"campaign_status"}),
             "Every active campaign with spend > 0 and revenue / spend < 2.5.",
             campaign_truth),
    Question("churn", "Analyze customer churn risk this month",
             frozenset({"customer_health"}),
             "The number of customers with status at_risk or churned.",
             churn_truth),
    Question("stores", "Compare store performance across regions",
             frozenset({"store_performance"}),
             "The stores with the lowest and highest revenue growth, last 90 days vs the prior 90.",
             store_truth),
    Question("margins", "Are discounts eroding our margins?",
             frozenset({"pricing_position"}),
             "Up to 3 products sold in the last 90 days whose average selling price is more than "
             "2% below list price, deepest discount first.",
             margin_truth),
    Question("revenue", "How has revenue changed over the last 90 days?",
             frozenset({"sales_summary"}),
             "Percentage change in revenue, last 90 days vs the prior 90, rounded to 0.1.",
             revenue_truth),
]

QUESTIONS_BY_ID = {q.id: q for q in QUESTIONS}
