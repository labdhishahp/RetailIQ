"""v1 API surface.

Read endpoints require an authenticated user; write endpoints additionally
require the manager role (see api/deps.py). Analytics responses are served
through a short TTL cache because each one aggregates a year of sales.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.v1.routes import auth as auth_routes
from app.api.v1.routes import copilot as copilot_routes
from app.api.v1.routes import insights as insight_routes
from app.api.v1.routes import operations as operations_routes
from app.models import User
from app.schemas.analytics import (
    CampaignPerformanceRow, CategorySalesRow, InventoryOverview, InventoryTrendPoint,
    KpiSummary, MonthlySalesPoint, ProductOverviewRow, RevenuePoint, SalesPeriodPoint,
    StoreComparisonRow, TopProductRow,
)
from app.schemas.campaign import CampaignRead
from app.schemas.customer import CustomerRead
from app.schemas.inventory import InventoryDetailRead
from app.schemas.product import ProductDetailRead
from app.schemas.sale import SaleDetailRead
from app.schemas.store import StoreRead
from app.services.analytics_service import analytics_service
from app.services.cache import cached
from app.services.campaign_service import campaign_service
from app.services.customer_service import customer_service
from app.services.inventory_service import inventory_service
from app.services.product_service import product_service
from app.services.sale_service import sale_service
from app.services.store_service import store_service

router = APIRouter()

# Composed route modules (each declares its own auth requirements)
router.include_router(auth_routes.router)
router.include_router(copilot_routes.router)
router.include_router(insight_routes.router)
router.include_router(operations_routes.router)

# Every remaining endpoint below requires a signed-in user.
protected = APIRouter(dependencies=[Depends(get_current_user)])


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------

@protected.get("/stores", response_model=list[StoreRead])
def list_stores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return store_service.list_stores(db, skip=skip, limit=limit)


@protected.get("/products", response_model=list[ProductDetailRead])
def list_products(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return product_service.list_products(db, skip=skip, limit=limit)


@protected.get("/inventory", response_model=list[InventoryDetailRead])
def list_inventory(skip: int = 0, limit: int = 300, db: Session = Depends(get_db)):
    return inventory_service.list_inventory(db, skip=skip, limit=limit)


@protected.get("/sales", response_model=list[SaleDetailRead])
def list_sales(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return sale_service.list_sales(db, skip=skip, limit=limit)


@protected.get("/customers", response_model=list[CustomerRead])
def list_customers(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return customer_service.list_customers(db, skip=skip, limit=limit)


@protected.get("/campaigns", response_model=list[CampaignRead])
def list_campaigns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return campaign_service.list_campaigns(db, skip=skip, limit=limit)


@protected.get("/products/{product_id}", response_model=ProductDetailRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    item = product_service.get_product(db, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return item


@protected.get("/stores/{store_id}", response_model=StoreRead)
def get_store(store_id: int, db: Session = Depends(get_db)):
    item = store_service.get_store(db, store_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return item


# --------------------------------------------------------------------------
# Analytics (cached)
# --------------------------------------------------------------------------

@protected.get("/analytics/kpis", response_model=KpiSummary)
def kpis(db: Session = Depends(get_db)):
    return cached("kpis", lambda: analytics_service.kpis(db))


@protected.get("/analytics/revenue-trend", response_model=list[RevenuePoint])
def revenue_trend(months: int = Query(12, ge=1, le=36), db: Session = Depends(get_db)):
    return cached(f"revenue_trend:{months}", lambda: analytics_service.revenue_trend(db, months))


@protected.get("/analytics/monthly-sales", response_model=list[MonthlySalesPoint])
def monthly_sales(months: int = Query(12, ge=1, le=36), db: Session = Depends(get_db)):
    return cached(f"monthly_sales:{months}", lambda: analytics_service.monthly_sales(db, months))


@protected.get("/analytics/sales", response_model=list[SalesPeriodPoint])
def sales_by_period(period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
                    db: Session = Depends(get_db)):
    return cached(f"sales:{period}", lambda: analytics_service.sales_by_period(db, period))


@protected.get("/analytics/store-comparison", response_model=list[StoreComparisonRow])
def store_comparison(db: Session = Depends(get_db)):
    return cached("store_comparison", lambda: analytics_service.store_comparison(db))


@protected.get("/analytics/category-sales", response_model=list[CategorySalesRow])
def category_sales(db: Session = Depends(get_db)):
    return cached("category_sales", lambda: analytics_service.category_sales(db))


@protected.get("/analytics/top-products", response_model=list[TopProductRow])
def top_products(limit: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    return cached(f"top_products:{limit}", lambda: analytics_service.top_products(db, limit))


@protected.get("/analytics/products-overview", response_model=list[ProductOverviewRow])
def products_overview(db: Session = Depends(get_db)):
    return cached("products_overview", lambda: analytics_service.products_overview(db))


@protected.get("/analytics/inventory-overview", response_model=InventoryOverview)
def inventory_overview(db: Session = Depends(get_db)):
    return cached("inventory_overview", lambda: analytics_service.inventory_overview(db))


@protected.get("/analytics/inventory-trend", response_model=list[InventoryTrendPoint])
def inventory_trend(db: Session = Depends(get_db)):
    return cached("inventory_trend", lambda: analytics_service.inventory_trend(db))


@protected.get("/analytics/campaign-performance", response_model=list[CampaignPerformanceRow])
def campaign_performance(db: Session = Depends(get_db)):
    return cached("campaign_performance", lambda: analytics_service.campaign_performance(db))


router.include_router(protected)
