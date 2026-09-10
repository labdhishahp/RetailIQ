from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money


class CustomerBase(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    segment: str = "Regular"
    total_orders: int = Field(default=0, ge=0)
    total_spent: Money = Field(default=Decimal("0.00"), ge=0)
    last_order_date: date | None = None
    status: str = "active"


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    segment: str | None = None
    total_orders: int | None = Field(default=None, ge=0)
    total_spent: Money | None = Field(default=None, ge=0)
    last_order_date: date | None = None
    status: str | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
