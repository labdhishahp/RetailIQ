from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.store import Store
from app.schemas.store import StoreRead


class StoreService:
    """Placeholder service layer for store operations."""

    def list_stores(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[StoreRead]:
        stores = db.scalars(select(Store).offset(skip).limit(limit)).all()
        return [StoreRead.model_validate(store) for store in stores]

    def get_store(self, db: Session, store_id: int) -> StoreRead | None:
        store = db.get(Store, store_id)
        return StoreRead.model_validate(store) if store else None


store_service = StoreService()
