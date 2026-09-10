from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    # Deliberately no length rule: a short password must fail authentication
    # with 401, not fail validation with 422, which would disclose the policy.
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    job_title: str | None = None
    location: str | None = None
    phone: str | None = None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    role: str = "analyst"


class UserUpdate(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    location: str | None = None
    phone: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class PreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    settings: dict
    theme: str


class PreferenceUpdate(BaseModel):
    settings: dict | None = None
    theme: str | None = None
