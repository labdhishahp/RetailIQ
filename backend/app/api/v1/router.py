from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.inventory import InventoryDetailRead
from app.schemas.product import ProductDetailRead
from app.schemas.sale import SaleDetailRead
from app.schemas.store import StoreRead
from app.services.inventory_service import inventory_service
from app.services.product_service import product_service
from app.services.sale_service import sale_service
from app.services.store_service import store_service

router = APIRouter()


@router.get("/stores", response_model=list[StoreRead])
def list_stores(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[StoreRead]:
    return store_service.list_stores(db, skip=skip, limit=limit)


@router.get("/products", response_model=list[ProductDetailRead])
def list_products(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ProductDetailRead]:
    return product_service.list_products(db, skip=skip, limit=limit)


@router.get("/inventory", response_model=list[InventoryDetailRead])
def list_inventory(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[InventoryDetailRead]:
    return inventory_service.list_inventory(db, skip=skip, limit=limit)


@router.get("/sales", response_model=list[SaleDetailRead])
def list_sales(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[SaleDetailRead]:
    return sale_service.list_sales(db, skip=skip, limit=limit)
