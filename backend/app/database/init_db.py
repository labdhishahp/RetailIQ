"""Database initialization and optional seed data."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import Category, Inventory, Product, Sale, SaleItem, Store

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def seed_sample_data(db: Session) -> None:
    """Seed minimal retail data for local development and demos."""
    if db.scalar(select(Store).limit(1)):
        logger.info("Sample data already present; skipping seed.")
        return

    stores = [
        Store(code="STR-DTN", name="Downtown", city="Metro City", region="Central", is_active=True),
        Store(code="STR-MLP", name="Mall Plaza", city="Metro City", region="East", is_active=True),
        Store(code="STR-APT", name="Airport", city="Metro City", region="South", is_active=True),
        Store(code="STR-SUB", name="Suburban", city="Greenfield", region="North", is_active=True),
        Store(code="STR-ONL", name="Online", city="Digital", region="Global", is_active=True),
    ]
    db.add_all(stores)
    db.flush()

    categories = [
        Category(name="Personal Care", slug="personal-care"),
        Category(name="Electronics", slug="electronics"),
        Category(name="Groceries", slug="groceries"),
        Category(name="Apparel", slug="apparel"),
        Category(name="Home & Living", slug="home-living"),
    ]
    db.add_all(categories)
    db.flush()

    products = [
        Product(
            sku="PRD-001",
            name="Premium Shampoo 500ml",
            category_id=categories[0].id,
            supplier="BeautyCare Ltd",
            price=Decimal("29.99"),
            cost=Decimal("12.50"),
            status="active",
        ),
        Product(
            sku="PRD-002",
            name="Wireless Earbuds Pro",
            category_id=categories[1].id,
            supplier="TechSound Inc",
            price=Decimal("49.99"),
            cost=Decimal("22.00"),
            status="low_stock",
        ),
        Product(
            sku="PRD-003",
            name="Organic Coffee Blend",
            category_id=categories[2].id,
            supplier="GreenBean Co",
            price=Decimal("19.99"),
            cost=Decimal("8.50"),
            status="active",
        ),
    ]
    db.add_all(products)
    db.flush()

    inventory_records = [
        Inventory(
            product_id=products[0].id,
            store_id=stores[0].id,
            quantity_on_hand=234,
            reorder_level=150,
            reorder_quantity=300,
            warehouse_name="Central DC",
        ),
        Inventory(
            product_id=products[1].id,
            store_id=stores[1].id,
            quantity_on_hand=89,
            reorder_level=150,
            reorder_quantity=200,
            warehouse_name="East Regional",
        ),
        Inventory(
            product_id=products[2].id,
            store_id=stores[2].id,
            quantity_on_hand=456,
            reorder_level=200,
            reorder_quantity=250,
            warehouse_name="West Regional",
        ),
    ]
    db.add_all(inventory_records)

    sale = Sale(
        store_id=stores[0].id,
        sale_number="SALE-20260716-001",
        sale_date=datetime(2026, 7, 16, 10, 30, tzinfo=timezone.utc),
        total_amount=Decimal("79.98"),
        total_items=2,
        status="completed",
    )
    db.add(sale)
    db.flush()

    sale_items = [
        SaleItem(
            sale_id=sale.id,
            product_id=products[0].id,
            quantity=1,
            unit_price=Decimal("29.99"),
            unit_cost=Decimal("12.50"),
            line_total=Decimal("29.99"),
        ),
        SaleItem(
            sale_id=sale.id,
            product_id=products[2].id,
            quantity=2,
            unit_price=Decimal("19.99"),
            unit_cost=Decimal("8.50"),
            line_total=Decimal("39.98"),
        ),
    ]
    db.add_all(sale_items)
    db.commit()
    logger.info("Sample retail data seeded successfully.")


def initialize_database(*, seed: bool = False) -> None:
    """Initialize database schema and optionally seed demo data."""
    init_db()
    if seed:
        db = SessionLocal()
        try:
            seed_sample_data(db)
        finally:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database(seed=True)
