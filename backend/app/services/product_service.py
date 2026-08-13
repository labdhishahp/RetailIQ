from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.schemas.product import ProductDetailRead


class ProductService:
    """Placeholder service layer for product operations."""

    def list_products(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ProductDetailRead]:
        products = db.scalars(
            select(Product)
            .options(selectinload(Product.category))
            .offset(skip)
            .limit(limit)
        ).all()
        return [ProductDetailRead.model_validate(product) for product in products]

    def get_product(self, db: Session, product_id: int) -> ProductDetailRead | None:
        product = db.scalar(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        return ProductDetailRead.model_validate(product) if product else None


product_service = ProductService()
