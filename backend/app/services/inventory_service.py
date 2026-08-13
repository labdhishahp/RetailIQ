from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.inventory import Inventory
from app.schemas.inventory import InventoryDetailRead


class InventoryService:
    """Placeholder service layer for inventory operations."""

    def list_inventory(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[InventoryDetailRead]:
        records = db.scalars(
            select(Inventory)
            .options(
                selectinload(Inventory.product),
                selectinload(Inventory.store),
            )
            .offset(skip)
            .limit(limit)
        ).all()
        return [InventoryDetailRead.model_validate(record) for record in records]

    def get_inventory(self, db: Session, inventory_id: int) -> InventoryDetailRead | None:
        record = db.scalar(
            select(Inventory)
            .options(
                selectinload(Inventory.product),
                selectinload(Inventory.store),
            )
            .where(Inventory.id == inventory_id)
        )
        return InventoryDetailRead.model_validate(record) if record else None


inventory_service = InventoryService()
