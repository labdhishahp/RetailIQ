from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CopilotQuery(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    conversation_id: int | None = None


class AgentTrace(BaseModel):
    id: str
    name: str
    icon: str
    task: str
    severity: str
    duration: int
    findings: list[dict]
    toolsCalled: list[str]


class Citation(BaseModel):
    title: str
    doc_type: str
    excerpt: str
    document_id: int
    chunk_id: int
    similarity: float | None = None


class InvestigationResult(BaseModel):
    rootCause: str
    evidence: list[str]
    confidence: int
    businessImpact: str
    riskLevel: str
    revenueImpact: float
    inventoryImpact: str
    suggestedCampaign: str
    priority: str
    nextSteps: list[str]
    agents: list[AgentTrace]
    citations: list[Citation] = []
    plan: dict
    elapsedMs: int
    synthesis: str


class CopilotResponse(BaseModel):
    conversation_id: int
    message_id: int
    question: str
    result: InvestigationResult


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    result: dict | None = None
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    doc_type: str
    source: str | None = None
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    content: str = Field(..., min_length=20)
    doc_type: str = "note"
    source: str | None = None


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    doc_type: str
    content: str
    score: float
    similarity: float | None = None
