from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.orchestrator import investigate
from app.api.deps import get_current_user, get_db, require_manager
from app.models import Conversation, Document, Message, User
from app.schemas.copilot import (
    ConversationDetail, ConversationRead, CopilotQuery, CopilotResponse,
    DocumentCreate, DocumentRead, SearchHit,
)
from app.services.rag_service import rag_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/query", response_model=CopilotResponse)
def query(payload: CopilotQuery, db: Session = Depends(get_db),
          user: User = Depends(get_current_user)):
    """Run the agent pipeline against live data and persist the exchange."""
    conversation = None
    if payload.conversation_id:
        conversation = db.get(Conversation, payload.conversation_id)
        if conversation and conversation.user_id not in (None, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation")
    if conversation is None:
        title = payload.question[:80]
        conversation = Conversation(title=title, user_id=user.id)
        db.add(conversation)
        db.flush()

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question))
    db.flush()

    result = investigate(db, payload.question, conversation_id=conversation.id)

    assistant = Message(
        conversation_id=conversation.id, role="assistant",
        content=result["rootCause"], result=result,
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)

    return CopilotResponse(
        conversation_id=conversation.id, message_id=assistant.id,
        question=payload.question, result=result,
    )


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(limit: int = Query(20, ge=1, le=100),
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(
        select(Conversation).where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc()).limit(limit)
    ).all()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    conversation = db.scalar(
        select(Conversation).options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id))
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id not in (None, user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id not in (None, user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")
    db.delete(conversation)
    db.commit()


# ---- knowledge base (RAG) ------------------------------------------------

@router.get("/documents", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Document).order_by(Document.created_at.desc())).all()


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_manager)):
    return rag_service.ingest(
        db, title=payload.title, content=payload.content,
        doc_type=payload.doc_type, source=payload.source, user_id=user.id)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db),
                    _: User = Depends(require_manager)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()


@router.get("/search", response_model=list[SearchHit])
def search(q: str = Query(..., min_length=2), limit: int = Query(5, ge=1, le=20),
           db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return rag_service.search(db, q, limit=limit)


@router.get("/knowledge-stats")
def knowledge_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return rag_service.stats(db)
