"""Document ingestion and hybrid retrieval over the knowledge base."""

import logging

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.embedding import chunk_text, embed

logger = logging.getLogger(__name__)


class RagService:
    def ingest(
        self,
        db: Session,
        *,
        title: str,
        content: str,
        doc_type: str = "note",
        source: str | None = None,
        user_id: int | None = None,
    ) -> Document:
        doc = Document(
            title=title, content=content, doc_type=doc_type,
            source=source, uploaded_by_id=user_id,
        )
        db.add(doc)
        db.flush()
        self._embed_document(db, doc)
        db.commit()
        db.refresh(doc)
        return doc

    def reindex(self, db: Session, doc: Document) -> None:
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        self._embed_document(db, doc)
        db.commit()

    def _embed_document(self, db: Session, doc: Document) -> None:
        for i, chunk in enumerate(chunk_text(doc.content)):
            db.add(DocumentChunk(
                document_id=doc.id, chunk_index=i, content=chunk,
                embedding=embed(f"{doc.title}\n\n{chunk}"),
            ))

    def search(self, db: Session, query: str, *, limit: int = 5) -> list[dict]:
        """Hybrid retrieval: vector similarity fused with full-text rank.

        Results from each retriever are combined with reciprocal rank fusion,
        which needs no score calibration between the two very different
        scoring scales.
        """
        if not query.strip():
            return []

        k = 60  # RRF damping constant
        fused: dict[int, dict] = {}

        vector_rows = db.execute(
            select(
                DocumentChunk.id, DocumentChunk.content, DocumentChunk.document_id,
                Document.title, Document.doc_type,
                DocumentChunk.embedding.cosine_distance(embed(query)).label("distance"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .order_by("distance")
            .limit(limit * 3)
        ).all()

        for rank, r in enumerate(vector_rows):
            fused[r.id] = {
                "chunk_id": r.id, "document_id": r.document_id, "title": r.title,
                "doc_type": r.doc_type, "content": r.content,
                "score": 1.0 / (k + rank + 1),
                "similarity": round(1.0 - float(r.distance), 4),
            }

        try:
            ts_rows = db.execute(
                text("""
                    SELECT c.id,
                           ts_rank(to_tsvector('english', c.content),
                                   plainto_tsquery('english', :q)) AS rank
                      FROM document_chunks c
                     WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', :q)
                     ORDER BY rank DESC
                     LIMIT :n
                """),
                {"q": query, "n": limit * 3},
            ).all()
            for rank, row in enumerate(ts_rows):
                if row.id in fused:
                    fused[row.id]["score"] += 1.0 / (k + rank + 1)
                else:
                    chunk = db.get(DocumentChunk, row.id)
                    if chunk:
                        fused[row.id] = {
                            "chunk_id": chunk.id, "document_id": chunk.document_id,
                            "title": chunk.document.title, "doc_type": chunk.document.doc_type,
                            "content": chunk.content, "score": 1.0 / (k + rank + 1),
                            "similarity": None,
                        }
        except Exception:  # pragma: no cover - FTS is an enhancement, not a requirement
            logger.warning("Full-text leg of hybrid search failed; using vector only.")

        ranked = sorted(fused.values(), key=lambda r: -r["score"])[:limit]
        for r in ranked:
            r["score"] = round(r["score"], 5)
        return ranked

    def stats(self, db: Session) -> dict:
        return {
            "documents": db.scalar(select(func.count()).select_from(Document)) or 0,
            "chunks": db.scalar(select(func.count()).select_from(DocumentChunk)) or 0,
        }


rag_service = RagService()
