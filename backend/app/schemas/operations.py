from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money


class StockAdjustment(BaseModel):
    product_id: int
    store_id: int
    quantity: int = Field(..., description="Signed: positive adds stock, negative removes")
    movement_type: str = Field("adjustment", pattern="^(restock|adjustment|return|transfer)$")
    note: str | None = None


class InventorySettingsUpdate(BaseModel):
    reorder_level: int | None = Field(None, ge=0)
    reorder_quantity: int | None = Field(None, ge=0)
    warehouse_name: str | None = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    store_id: int
    movement_type: str
    quantity: int
    balance_after: int
    reference: str | None = None
    note: str | None = None
    occurred_at: datetime


class SaleLineCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float | None = None


class SaleCreateRequest(BaseModel):
    store_id: int
    customer_id: int | None = None
    items: list[SaleLineCreate] = Field(..., min_length=1)


class PurchaseOrderCreate(BaseModel):
    product_id: int
    store_id: int
    quantity: int = Field(..., gt=0)
    note: str | None = None


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    product_id: int
    store_id: int
    quantity: int
    unit_cost: Money
    total_cost: Money
    status: str
    supplier: str | None = None
    expected_date: date | None = None
    created_at: datetime


class Page(BaseModel):
    """Envelope for paginated list endpoints."""

    items: list
    total: int
    skip: int
    limit: int
