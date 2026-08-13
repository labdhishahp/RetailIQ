from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.schemas.sale import SaleDetailRead


class SaleService:
    """Placeholder service layer for sales operations."""

    def list_sales(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SaleDetailRead]:
        sales = db.scalars(
            select(Sale)
            .options(
                selectinload(Sale.store),
                selectinload(Sale.items).selectinload(SaleItem.product),
            )
            .offset(skip)
            .limit(limit)
        ).all()
        return [SaleDetailRead.model_validate(sale) for sale in sales]

    def get_sale(self, db: Session, sale_id: int) -> SaleDetailRead | None:
        sale = db.scalar(
            select(Sale)
            .options(
                selectinload(Sale.store),
                selectinload(Sale.items).selectinload(SaleItem.product),
            )
            .where(Sale.id == sale_id)
        )
        return SaleDetailRead.model_validate(sale) if sale else None


sale_service = SaleService()
