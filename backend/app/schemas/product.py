from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead
from app.schemas.common import Money


class ProductBase(BaseModel):
    sku: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    description: str | None = None
    category_id: int
    supplier: str | None = None
    price: Money = Field(..., ge=0)
    cost: Money = Field(..., ge=0)
    status: str = "active"


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category_id: int | None = None
    supplier: str | None = None
    price: Money | None = Field(default=None, ge=0)
    cost: Money | None = Field(default=None, ge=0)
    status: str | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProductDetailRead(ProductRead):
    category: CategoryRead | None = None
