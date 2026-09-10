"""Database initialization and seed data.

Seeds a realistic multi-store retail dataset: 6 categories, 5 stores, 24
products, per-store inventory, 40 customers, 8 campaigns, and 12 months of
sales history. Volumes are chosen so the dashboard analytics (trends, growth,
category mix, stock health) have enough data to render meaningfully.

Seeding is idempotent: if stores already exist it is skipped unless the caller
passes reset=True, which clears transactional and catalogue tables first.
"""

import logging
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session


from app.core.security import hash_password
from app.database.base import Base
from app.database.seed_knowledge import DOCUMENTS
from app.database.session import SessionLocal, engine
from app.models import (
    AgentRun,
    Alert,
    Campaign,
    Category,
    Conversation,
    Customer,
    Decision,
    Document,
    DocumentChunk,
    Inventory,
    Message,
    Product,
    PurchaseOrder,
    Recommendation,
    Report,
    Sale,
    SaleItem,
    Simulation,
    StockMovement,
    Store,
    User,
    UserPreference,
)

logger = logging.getLogger(__name__)

SEED = 20260910  # fixed so re-seeding reproduces the same dataset

CATEGORIES = [
    ("Personal Care", "personal-care"),
    ("Electronics", "electronics"),
    ("Groceries", "groceries"),
    ("Apparel", "apparel"),
    ("Home & Living", "home-living"),
    ("Sports & Outdoors", "sports-outdoors"),
]

STORES = [
    ("STR-DTN", "Downtown", "Metro City", "Central"),
    ("STR-MLP", "Mall Plaza", "Metro City", "East"),
    ("STR-APT", "Airport", "Metro City", "South"),
    ("STR-SUB", "Suburban", "Greenfield", "North"),
    ("STR-ONL", "Online", "Digital", "Global"),
]

WAREHOUSES = ["Central DC", "East Regional", "West Regional"]

# Share of sale lines that transact below list price, by category. Personal
# Care is the most promotionally-driven category in this business.
PROMO_RATE = {
    "Personal Care": 0.34, "Apparel": 0.28, "Electronics": 0.22,
    "Home & Living": 0.16, "Groceries": 0.12, "Sports & Outdoors": 0.18,
}

# Seasonal/discontinued lines: they sold earlier in the year but have had no
# movement for months, so they surface as genuine dead stock.
DISCONTINUED_SKUS = {"PRD-015", "PRD-018"}
DISCONTINUED_AFTER_DAYS = 150  # no sales within this many days of "now"

# (sku, name, category index, supplier, price, cost, demand weight)
PRODUCTS = [
    ("PRD-001", "Premium Shampoo 500ml",   0, "BeautyCare Ltd",  29.99,  12.50, 9),
    ("PRD-002", "Wireless Earbuds Pro",    1, "TechSound Inc",   49.99,  22.00, 8),
    ("PRD-003", "Organic Coffee Blend",    2, "GreenBean Co",    19.99,   8.50, 10),
    ("PRD-004", "Running Shoes X200",      3, "SportFlex",       79.99,  35.00, 6),
    ("PRD-005", "Smart Watch Series 5",    1, "TechSound Inc",  199.99,  95.00, 4),
    ("PRD-006", "Conditioner 400ml",       0, "BeautyCare Ltd",  24.99,  10.00, 7),
    ("PRD-007", "Face Moisturizer",        0, "BeautyCare Ltd",  34.99,  14.00, 6),
    ("PRD-008", "LED Desk Lamp",           4, "HomeGlow",        44.99,  18.00, 5),
    ("PRD-009", "Yoga Mat Premium",        5, "SportFlex",       39.99,  15.00, 5),
    ("PRD-010", "Protein Powder 2kg",      2, "NutriMax",        54.99,  28.00, 6),
    ("PRD-011", "Bluetooth Speaker Mini",  1, "TechSound Inc",   34.99,  14.50, 7),
    ("PRD-012", "Cotton T-Shirt Pack",     3, "FashionHub",      29.99,  12.00, 8),
    ("PRD-013", "Body Wash 750ml",         0, "BeautyCare Ltd",  18.99,   7.20, 7),
    ("PRD-014", "Stainless Water Bottle",  5, "SportFlex",       24.99,   9.00, 6),
    ("PRD-015", "Winter Jacket XL",        3, "FashionHub",     129.99,  58.00, 1),
    ("PRD-016", "Green Tea 100 Bags",      2, "GreenBean Co",    14.99,   5.50, 8),
    ("PRD-017", "Ceramic Dinner Set",      4, "HomeGlow",        89.99,  38.00, 3),
    ("PRD-018", "Phone Case Clear",        1, "TechSound Inc",    12.99,  3.80, 2),
    ("PRD-019", "Resistance Band Set",     5, "SportFlex",       21.99,   7.50, 5),
    ("PRD-020", "Scented Candle Trio",     4, "HomeGlow",        27.99,  10.50, 4),
    ("PRD-021", "Almond Butter 500g",      2, "NutriMax",        16.99,   6.80, 6),
    ("PRD-022", "Denim Jeans Slim",        3, "FashionHub",      69.99,  29.00, 5),
    ("PRD-023", "Hair Serum 100ml",        0, "BeautyCare Ltd",  39.99,  16.00, 4),
    ("PRD-024", "Laptop Stand Alloy",      4, "HomeGlow",        49.99,  20.00, 4),
]

FIRST_NAMES = ["Sarah", "James", "Emily", "Michael", "Lisa", "David", "Anna", "Robert",
               "Priya", "Daniel", "Maria", "Kevin", "Sofia", "Omar", "Grace", "Ethan",
               "Nina", "Lucas", "Aisha", "Tom"]
LAST_NAMES = ["Mitchell", "Chen", "Rodriguez", "Park", "Thompson", "Wilson", "Kowalski",
              "Singh", "Patel", "Nguyen", "Silva", "Okafor", "Muller", "Rossi",
              "Andersen", "Haddad", "Kim", "Novak", "Dubois", "Reyes"]

CAMPAIGNS = [
    ("CMP-001", "Summer Sale 2026",        "Social Media", "active",     85000,  62400, 131040, 2400000, 8420, -100, 20),
    ("CMP-002", "Back to School",          "Search Ads",   "scheduled", 120000,      0,      0,       0,    0,   20, 65),
    ("CMP-003", "Electronics Flash Sale",  "Email",        "completed",  45000,  44800, 188160,  890000, 3210, -160, -140),
    ("CMP-004", "Personal Care Bundle",    "Email",        "active",     35000,  28900,  52020, 1200000, 4560,  -70, -10),
    ("CMP-005", "Holiday Preview",         "Display",      "draft",     200000,      0,      0,       0,    0,   60, 120),
    ("CMP-006", "Loyalty Win-Back",        "Email",        "active",     28000,  19600,  74480,  640000, 2870,  -45, 15),
    ("CMP-007", "Fitness January Push",    "Social Media", "completed",  52000,  51200, 107520, 1450000, 5130, -240, -200),
    ("CMP-008", "Home Refresh Weekend",    "Display",      "completed",  31000,  30100,  45150,  780000, 1920, -120, -110),
]


def init_db(*, recreate: bool = False) -> None:
    """Create all database tables.

    create_all() never ALTERs an existing table, so when the models gain a
    column the schema silently drifts. recreate=True drops the known tables
    first, guaranteeing the database matches the models.
    """
    with engine.begin() as conn:
        # document_chunks.embedding needs pgvector
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    if recreate:
        Base.metadata.drop_all(bind=engine)
        logger.info("Existing tables dropped.")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


DEFAULT_USERS = [
    ("admin@retailiq.app", "Labdhi Shah", "admin", "Head of Retail Operations"),
    ("manager@retailiq.app", "Priya Raman", "manager", "Category Manager"),
    ("analyst@retailiq.app", "Sam Okafor", "analyst", "Business Analyst"),
]
DEFAULT_PASSWORD = "RetailIQ2026!"


def _clear(db: Session) -> None:
    """Remove seeded rows in FK-safe order."""
    for model in (AgentRun, Message, Conversation, DocumentChunk, Document,
                  Decision, Recommendation, Simulation, Report, Alert,
                  PurchaseOrder, StockMovement, UserPreference,
                  SaleItem, Sale, Inventory, Campaign, Customer, Product,
                  Category, Store, User):
        db.execute(delete(model))
    db.commit()
    logger.info("Existing seed data cleared.")


def seed_sample_data(db: Session) -> None:
    """Seed a realistic multi-store retail dataset."""
    rng = random.Random(SEED)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    stores = [Store(code=c, name=n, city=ct, region=r, is_active=True)
              for c, n, ct, r in STORES]
    db.add_all(stores)

    categories = [Category(name=n, slug=s) for n, s in CATEGORIES]
    db.add_all(categories)
    db.flush()

    products = [
        Product(sku=sku, name=name, category_id=categories[ci].id, supplier=sup,
                price=Decimal(str(price)), cost=Decimal(str(cost)), status="active")
        for sku, name, ci, sup, price, cost, _ in PRODUCTS
    ]
    db.add_all(products)
    db.flush()

    weights = {p.id: PRODUCTS[i][6] for i, p in enumerate(products)}

    # ---- inventory: every product stocked in 3-5 stores --------------------
    inventory_rows = []
    for idx, product in enumerate(products):
        demand = weights[product.id]
        for store in rng.sample(stores, rng.randint(3, 5)):
            reorder_level = max(20, demand * 6)
            # Deliberately spread stock health across the fleet so the
            # inventory page shows healthy, low and overstocked rows.
            roll = rng.random()
            if roll < 0.18:
                qty = rng.randint(2, max(3, reorder_level - 5))  # low stock
            elif roll < 0.30:
                lo = reorder_level * 2 + 10
                qty = rng.randint(lo, lo + reorder_level + 40)              # overstock
            else:
                qty = rng.randint(reorder_level + 20, reorder_level * 2)      # healthy
            inventory_rows.append(Inventory(
                product_id=product.id, store_id=store.id,
                quantity_on_hand=qty, reorder_level=reorder_level,
                reorder_quantity=max(40, demand * 10),
                warehouse_name=WAREHOUSES[idx % len(WAREHOUSES)],
            ))
    db.add_all(inventory_rows)

    # ---- customers ---------------------------------------------------------
    customers = []
    for i in range(40):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 7) % len(LAST_NAMES)]
        customers.append(Customer(
            code=f"CUS-{i + 1:03d}",
            name=f"{first} {last}",
            email=f"{first.lower()}.{last.lower()}{i}@example.com",
            segment=rng.choices(["Regular", "Premium", "VIP"], weights=[6, 3, 1])[0],
            status="active", total_orders=0, total_spent=Decimal("0.00"),
        ))
    db.add_all(customers)
    db.flush()

    # ---- campaigns ---------------------------------------------------------
    today = date.today()
    db.add_all([
        Campaign(code=code, name=name, channel=ch, status=st,
                 budget=Decimal(str(b)), spent=Decimal(str(sp)), revenue=Decimal(str(rev)),
                 impressions=imp, conversions=conv,
                 start_date=today + timedelta(days=sd), end_date=today + timedelta(days=ed))
        for code, name, ch, st, b, sp, rev, imp, conv, sd, ed in CAMPAIGNS
    ])

    # ---- 12 months of sales ------------------------------------------------
    product_by_id = {p.id: p for p in products}
    category_by_product = {p.id: CATEGORIES[PRODUCTS[i][2]][0] for i, p in enumerate(products)}
    inv_by_product: dict[int, list[int]] = {}
    for row in inventory_rows:
        inv_by_product.setdefault(row.product_id, []).append(row.store_id)

    # ~20% of the base lapses at some point in the year
    lapse_after = {}
    for c in customers:
        roll = rng.random()
        if roll < 0.12:
            lapse_after[c.id] = rng.randint(70, 200)    # churned (no orders for months)
        elif roll < 0.22:
            lapse_after[c.id] = rng.randint(35, 69)     # at risk
    weighted_ids = [pid for pid, w in weights.items() for _ in range(w)]
    discontinued_ids = {p.id for p in products if p.sku in DISCONTINUED_SKUS}
    active_ids = [pid for pid in weighted_ids if pid not in discontinued_ids]
    sales, items, counters = [], [], {}
    cust_totals: dict[int, list] = {c.id: [0, Decimal("0.00"), None] for c in customers}

    for day_offset in range(365, -1, -1):
        day = now - timedelta(days=day_offset)
        # seasonal lift towards year end + weekend lift + mild upward trend
        seasonal = 1.0 + 0.25 * (1 - day_offset / 365)
        weekend = 1.35 if day.weekday() >= 5 else 1.0
        n_sales = max(1, int(rng.gauss(6, 2) * seasonal * weekend))

        for _ in range(n_sales):
            store = rng.choice(stores)
            customer = None
            if rng.random() < 0.85:
                # lapsed customers stop transacting partway through the year,
                # which is what produces genuine at-risk / churned segments
                eligible = [c for c in customers
                            if day_offset >= lapse_after.get(c.id, -1)]
                customer = rng.choice(eligible) if eligible else None
            ts = day.replace(hour=rng.randint(8, 20), minute=rng.choice([0, 15, 30, 45]))
            key = ts.strftime("%Y%m%d")
            counters[key] = counters.get(key, 0) + 1
            sale = Sale(
                store_id=store.id,
                customer_id=customer.id if customer else None,
                sale_number=f"SALE-{key}-{counters[key]:04d}",
                sale_date=ts, total_amount=Decimal("0.00"), total_items=0,
                status="completed",
            )
            sales.append(sale)

            pool = active_ids if day_offset < DISCONTINUED_AFTER_DAYS else weighted_ids
            chosen = rng.sample(pool, k=min(rng.randint(1, 4), len(pool)))
            total, count, lines = Decimal("0.00"), 0, []
            for pid in set(chosen):
                if store.id not in inv_by_product.get(pid, []):
                    continue
                product = product_by_id[pid]
                qty = rng.randint(1, 3)
                # Realistic promotional behaviour: a share of lines sell below
                # list. Promo-heavy categories discount more often and deeper,
                # which is what gives the pricing analysis real signal.
                promo_rate = PROMO_RATE.get(category_by_product[pid], 0.10)
                if rng.random() < promo_rate:
                    discount = Decimal(str(round(rng.uniform(0.05, 0.25), 2)))
                    unit_price = (product.price * (1 - discount)).quantize(Decimal("0.01"))
                else:
                    unit_price = product.price
                line_total = (unit_price * qty).quantize(Decimal("0.01"))
                lines.append((pid, qty, unit_price, product.cost, line_total))
                total += line_total
                count += qty
            if not lines:
                sales.pop()
                continue
            sale.total_amount, sale.total_items = total, count
            items.append((sale, lines))
            if customer:
                agg = cust_totals[customer.id]
                agg[0] += 1
                agg[1] += total
                agg[2] = ts.date()

    db.add_all(sales)
    db.flush()

    sale_items = [
        SaleItem(sale_id=sale.id, product_id=pid, quantity=qty,
                 unit_price=price, unit_cost=cost, line_total=line_total)
        for sale, lines in items
        for pid, qty, price, cost, line_total in lines
    ]
    db.bulk_save_objects(sale_items)

    # ---- roll customer aggregates up from their real sales -----------------
    spends = sorted((cust_totals[c.id][1] for c in customers), reverse=True)
    vip_cut = spends[max(0, int(len(spends) * 0.15) - 1)] if spends else Decimal("0")
    premium_cut = spends[max(0, int(len(spends) * 0.45) - 1)] if spends else Decimal("0")
    today = date.today()

    for customer in customers:
        orders, spent, last = cust_totals[customer.id]
        customer.total_orders = orders
        customer.total_spent = spent
        customer.last_order_date = last
        days_since = (today - last).days if last else None
        if orders == 0 or (days_since is not None and days_since > 120):
            customer.status = "churned"
        elif days_since is not None and days_since > 60:
            customer.status = "at_risk"
        else:
            customer.status = "active"
        # Segments are relative to the customer base rather than absolute
        # thresholds, so the mix stays meaningful at any transaction volume.
        if spent >= vip_cut and spent > 0:
            customer.segment = "VIP"
        elif spent >= premium_cut:
            customer.segment = "Premium"
        else:
            customer.segment = "Regular"

    # ---- derive product status from real stock position --------------------
    stock_by_product: dict[int, int] = {}
    level_by_product: dict[int, int] = {}
    for row in inventory_rows:
        stock_by_product[row.product_id] = stock_by_product.get(row.product_id, 0) + row.quantity_on_hand
        level_by_product[row.product_id] = level_by_product.get(row.product_id, 0) + row.reorder_level
    for product in products:
        stock = stock_by_product.get(product.id, 0)
        level = level_by_product.get(product.id, 0)
        if stock == 0:
            product.status = "out_of_stock"
        elif stock <= level:
            product.status = "low_stock"
        elif level and stock > level * 2:
            product.status = "overstock"
        else:
            product.status = "active"

    db.commit()
    logger.info(
        "Seeded %d stores, %d categories, %d products, %d inventory rows, "
        "%d customers, %d campaigns, %d sales, %d sale items.",
        len(stores), len(categories), len(products), len(inventory_rows),
        len(customers), len(CAMPAIGNS), len(sales), len(sale_items),
    )

    seed_users(db)
    seed_documents(db)
    seed_intelligence(db)


def seed_users(db: Session) -> None:
    """Create the default accounts if they do not already exist."""
    created = 0
    for email, name, role, title in DEFAULT_USERS:
        if db.scalar(select(User).where(User.email == email)):
            continue
        db.add(User(
            email=email, full_name=name, role=role, job_title=title,
            hashed_password=hash_password(DEFAULT_PASSWORD),
            location="Mumbai, India", is_active=True,
        ))
        created += 1
    db.commit()
    logger.info("Seeded %d user account(s). Default password: %s", created, DEFAULT_PASSWORD)


def seed_documents(db: Session) -> None:
    """Ingest the knowledge-base corpus and build its embeddings."""
    from app.services.rag_service import rag_service

    created = 0
    for doc in DOCUMENTS:
        if db.scalar(select(Document).where(Document.title == doc["title"])):
            continue
        rag_service.ingest(
            db, title=doc["title"], content=doc["content"],
            doc_type=doc["doc_type"], source=doc["source"],
        )
        created += 1
    chunks = db.scalar(select(func.count()).select_from(DocumentChunk)) or 0
    logger.info("Seeded %d knowledge document(s), %d embedded chunk(s).", created, chunks)


def seed_intelligence(db: Session) -> None:
    """Run the first sweeps so the application opens with real content."""
    from app.services.alert_service import alert_service
    from app.services.recommendation_service import recommendation_service
    from app.services.report_service import report_service

    recs = recommendation_service.generate(db)
    alerts = alert_service.evaluate(db)

    # Two reports generated from the seeded data, so the Reports page is not
    # empty on first sign-in. Both are produced by the real generator.
    reports = [report_service.generate(db, kind=k) for k in ("weekly", "inventory")]

    logger.info("Generated %d recommendation(s), %d alert(s), %d report(s).",
                len(recs), len(alerts), len(reports))


def initialize_database(*, seed: bool = False, reset: bool = False,
                        recreate: bool = False) -> None:
    """Create schema and optionally seed demo data."""
    init_db(recreate=recreate)
    if recreate:
        reset = False  # tables are already empty
    if not seed:
        return
    db = SessionLocal()
    try:
        if reset:
            _clear(db)
        elif db.scalar(select(Store).limit(1)):
            logger.info("Sample data already present; skipping seed. Use reset=True to replace.")
            return
        seed_sample_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    initialize_database(
        seed=True,
        reset="--reset" in sys.argv,
        recreate="--recreate" in sys.argv,
    )
