from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_manager
from app.models import PurchaseOrder, StockMovement, User
from app.schemas.operations import (
    InventorySettingsUpdate, PurchaseOrderCreate, PurchaseOrderRead, SaleCreateRequest,
    StockAdjustment, StockMovementRead,
)
from app.schemas.product import ProductCreate, ProductDetailRead, ProductUpdate
from app.schemas.sale import SaleDetailRead
from app.services.operations_service import OperationsError, operations_service

router = APIRouter(tags=["operations"])


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except OperationsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ---- catalogue -----------------------------------------------------------

@router.post("/products", response_model=ProductDetailRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db),
                   _: User = Depends(require_manager)):
    return _guard(operations_service.create_product, db, payload.model_dump())


@router.patch("/products/{product_id}", response_model=ProductDetailRead)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db),
                   _: User = Depends(require_manager)):
    return _guard(operations_service.update_product, db, product_id,
                  payload.model_dump(exclude_none=True))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db),
                   _: User = Depends(require_manager)):
    _guard(operations_service.delete_product, db, product_id)


# ---- stock ---------------------------------------------------------------

@router.post("/inventory/adjust", response_model=StockMovementRead,
             status_code=status.HTTP_201_CREATED)
def adjust_stock(payload: StockAdjustment, db: Session = Depends(get_db),
                 _: User = Depends(require_manager)):
    return _guard(
        operations_service.record_movement, db,
        product_id=payload.product_id, store_id=payload.store_id,
        quantity=payload.quantity, movement_type=payload.movement_type, note=payload.note)


@router.patch("/inventory/{inventory_id}")
def update_inventory_settings(inventory_id: int, payload: InventorySettingsUpdate,
                              db: Session = Depends(get_db), _: User = Depends(require_manager)):
    inv = _guard(operations_service.update_inventory_settings, db, inventory_id,
                 **payload.model_dump(exclude_none=True))
    return {"id": inv.id, "reorder_level": inv.reorder_level,
            "reorder_quantity": inv.reorder_quantity, "warehouse_name": inv.warehouse_name}


@router.get("/stock-movements", response_model=list[StockMovementRead])
def list_movements(product_id: int | None = None, limit: int = Query(50, ge=1, le=200),
                   db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = select(StockMovement).order_by(StockMovement.occurred_at.desc()).limit(limit)
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    return db.scalars(q).all()


# ---- sales ---------------------------------------------------------------

@router.post("/sales", response_model=SaleDetailRead, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreateRequest, db: Session = Depends(get_db),
                _: User = Depends(require_manager)):
    return _guard(
        operations_service.create_sale, db, store_id=payload.store_id,
        customer_id=payload.customer_id,
        items=[i.model_dump() for i in payload.items])


# ---- purchase orders -----------------------------------------------------

@router.get("/purchase-orders", response_model=list[PurchaseOrderRead])
def list_purchase_orders(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
                         _: User = Depends(get_current_user)):
    return db.scalars(
        select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(limit)).all()


@router.post("/purchase-orders", response_model=PurchaseOrderRead,
             status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db),
                          user: User = Depends(require_manager)):
    return _guard(
        operations_service.create_purchase_order, db, product_id=payload.product_id,
        store_id=payload.store_id, quantity=payload.quantity, user_id=user.id,
        note=payload.note)


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderRead)
def receive_purchase_order(po_id: int, db: Session = Depends(get_db),
                           _: User = Depends(require_manager)):
    return _guard(operations_service.receive_purchase_order, db, po_id)
