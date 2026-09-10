from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money
from app.schemas.product import ProductRead


class SaleItemBase(BaseModel):
    sale_id: int
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Money = Field(..., ge=0)
    unit_cost: Money = Field(..., ge=0)
    line_total: Money = Field(..., ge=0)


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    unit_price: Money | None = Field(default=None, ge=0)
    unit_cost: Money | None = Field(default=None, ge=0)
    line_total: Money | None = Field(default=None, ge=0)


class SaleItemRead(SaleItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SaleItemDetailRead(SaleItemRead):
    product: ProductRead | None = None
