from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    kind: str
    title: str
    rationale: str
    impact: str
    revenue_impact: Money
    confidence: int
    priority: str
    status: str
    evidence: dict
    product_id: int | None = None
    store_id: int | None = None
    created_at: datetime


class RecommendationAction(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected)$")
    note: str | None = None


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    question: str
    recommendation_text: str
    status: str
    outcome: str | None = None
    impact: str | None = None
    roi: int | None = None
    confidence: int
    decided_on: date
    created_at: datetime


class DecisionCreate(BaseModel):
    question: str
    recommendation_text: str
    status: str = "pending"
    impact: str | None = None
    confidence: int = 0
    recommendation_id: int | None = None
    conversation_id: int | None = None
    simulation_id: int | None = None


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    severity: str
    title: str
    message: str
    category: str
    is_read: bool
    occurred_at: datetime


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    kind: str
    status: str
    summary: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    created_at: datetime


class ReportDetail(ReportRead):
    payload: dict


class ReportCreate(BaseModel):
    kind: str = Field("weekly", pattern="^(weekly|monthly|inventory|campaign|customer)$")


class SimulationRequest(BaseModel):
    name: str = Field("Scenario", max_length=255)
    discount_pct: float = Field(..., ge=0, le=90)
    duration_days: int = Field(28, ge=1, le=365)
    product_skus: list[str] | None = None
    category: str | None = None
    extra_spend: float = Field(0, ge=0)


class SimulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    scenario: dict
    results: dict
    summary: str | None = None
    created_at: datetime
