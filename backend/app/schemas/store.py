from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=255)
    location: str | None = None
    city: str | None = None
    region: str | None = None
    is_active: bool = True
    description: str | None = None


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    location: str | None = None
    city: str | None = None
    region: str | None = None
    is_active: bool | None = None
    description: str | None = None


class StoreRead(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
