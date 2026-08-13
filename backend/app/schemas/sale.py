from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.sale_item import SaleItemRead
from app.schemas.store import StoreRead


class SaleBase(BaseModel):
    store_id: int
    sale_number: str = Field(..., max_length=64)
    sale_date: datetime
    total_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_items: int = Field(default=0, ge=0)
    status: str = "completed"


class SaleCreate(SaleBase):
    pass


class SaleUpdate(BaseModel):
    store_id: int | None = None
    sale_number: str | None = Field(default=None, max_length=64)
    sale_date: datetime | None = None
    total_amount: Decimal | None = Field(default=None, ge=0)
    total_items: int | None = Field(default=None, ge=0)
    status: str | None = None


class SaleRead(SaleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SaleDetailRead(SaleRead):
    store: StoreRead | None = None
    items: list[SaleItemRead] = []
