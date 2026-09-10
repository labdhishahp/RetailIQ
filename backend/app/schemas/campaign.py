from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money


class CampaignBase(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=255)
    channel: str = "Email"
    status: str = "draft"
    budget: Money = Field(default=Decimal("0.00"), ge=0)
    spent: Money = Field(default=Decimal("0.00"), ge=0)
    revenue: Money = Field(default=Decimal("0.00"), ge=0)
    impressions: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    start_date: date | None = None
    end_date: date | None = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    channel: str | None = None
    status: str | None = None
    budget: Money | None = Field(default=None, ge=0)
    spent: Money | None = Field(default=None, ge=0)
    revenue: Money | None = Field(default=None, ge=0)
    impressions: int | None = Field(default=None, ge=0)
    conversions: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None


class CampaignRead(CampaignBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
