"""Test fixtures.

Tests run against a dedicated schema in the same database so they exercise
real PostgreSQL behaviour (pgvector, date_trunc, JSONB) rather than a SQLite
stand-in that would not support them. The schema is created and dropped per
session, so the application data is never touched.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  -- registers every table on Base.metadata
from app.core.config import settings
from app.core.security import hash_password
from app.database.base import Base

TEST_SCHEMA = f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def engine():
    """Engine bound to a throwaway schema.

    search_path cannot be used for this: the Supabase connection is a pgBouncer
    transaction pooler, which does not preserve session-level settings. SQLAlchemy's
    schema_translate_map rewrites the schema per statement instead, so isolation
    holds regardless of pooling mode.
    """
    admin = create_engine(settings.database_url, pool_pre_ping=True)
    with admin.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{TEST_SCHEMA}"'))

    eng = admin.execution_options(schema_translate_map={None: TEST_SCHEMA})
    Base.metadata.create_all(bind=eng, checkfirst=False)

    with admin.connect() as conn:
        placed = conn.execute(text(
            "select count(*) from information_schema.tables where table_schema = :s"
        ), {"s": TEST_SCHEMA}).scalar()
        assert placed >= 20, f"expected the model set in {TEST_SCHEMA}, found {placed}"

    yield eng

    with admin.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
    admin.dispose()


@pytest.fixture(scope="session")
def SessionLocal(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture
def db(SessionLocal):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def client(engine, SessionLocal):
    """App wired to the test schema."""
    from app.api.deps import get_db
    from app.main import app

    def override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def seeded(engine, SessionLocal):
    """A small but complete dataset: catalogue, stock, sales, users, docs."""
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from app.models import (
        Campaign, Category, Customer, Inventory, Product, Sale, SaleItem, Store, User,
    )
    from app.services.rag_service import rag_service

    db = SessionLocal()
    store = Store(code="T-ST1", name="Test Store", city="Testville", region="T", is_active=True)
    cat = Category(name="TestCat", slug="testcat")
    db.add_all([store, cat])
    db.flush()

    fast = Product(sku="T-001", name="Fast Mover", category_id=cat.id, supplier="S1",
                   price=Decimal("20.00"), cost=Decimal("8.00"), status="active")
    slow = Product(sku="T-002", name="Slow Mover", category_id=cat.id, supplier="S1",
                   price=Decimal("50.00"), cost=Decimal("25.00"), status="active")
    db.add_all([fast, slow])
    db.flush()

    db.add_all([
        # 15 on hand against ~1 unit/day of demand -> ~15 days cover, which is
        # inside the 21-day threshold the stockout rule fires on.
        Inventory(product_id=fast.id, store_id=store.id, quantity_on_hand=15,
                  reorder_level=100, reorder_quantity=200, warehouse_name="T-DC"),
        Inventory(product_id=slow.id, store_id=store.id, quantity_on_hand=500,
                  reorder_level=50, reorder_quantity=60, warehouse_name="T-DC"),
    ])

    customer = Customer(code="T-C1", name="Test Buyer", email="buyer@retailiq-test.com",
                        segment="Regular", status="active")
    db.add(customer)
    db.add(Campaign(code="T-CMP1", name="Weak Campaign", channel="Email", status="active",
                    budget=Decimal("1000"), spent=Decimal("1000"), revenue=Decimal("1000"),
                    impressions=100, conversions=10))
    db.flush()

    # Bulk-inserted: the test database is remote, so per-row flushes dominate
    # the suite's runtime.
    now = datetime.now(timezone.utc)
    sales = [
        Sale(store_id=store.id, customer_id=customer.id,
             sale_number=f"T-SALE-{i:04d}", sale_date=now - timedelta(days=i),
             total_amount=Decimal("40.00"), total_items=2, status="completed")
        for i in range(45)
    ]
    db.add_all(sales)
    db.flush()
    db.bulk_save_objects([
        SaleItem(sale_id=sale.id, product_id=fast.id, quantity=2,
                 unit_price=Decimal("20.00"), unit_cost=Decimal("8.00"),
                 line_total=Decimal("40.00"))
        for sale in sales
    ])

    db.add_all([
        User(email="t-admin@retailiq-test.com", full_name="T Admin", role="admin",
             hashed_password=hash_password("TestPass123!"), is_active=True),
        User(email="t-analyst@retailiq-test.com", full_name="T Analyst", role="analyst",
             hashed_password=hash_password("TestPass123!"), is_active=True),
    ])
    db.commit()

    rag_service.ingest(
        db, title="Test Replenishment Policy", doc_type="policy",
        content=("Reorder triggers. A location must raise a purchase order when on-hand "
                 "quantity falls to or below the reorder level.\n\n"
                 "Cover targets. The business targets thirty to forty five days of cover "
                 "for fast moving lines."))

    # Read the identifiers while the session is still open: after close() the
    # instances are detached and any attribute access would re-query.
    ids = {"store_id": store.id, "fast_id": fast.id, "slow_id": slow.id,
           "customer_id": customer.id, "category_id": cat.id}
    db.close()
    return ids


@pytest.fixture(scope="session")
def admin_token(client, seeded):
    r = client.post("/api/v1/auth/login",
                    json={"email": "t-admin@retailiq-test.com", "password": "TestPass123!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def analyst_token(client, seeded):
    r = client.post("/api/v1/auth/login",
                    json={"email": "t-analyst@retailiq-test.com", "password": "TestPass123!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
