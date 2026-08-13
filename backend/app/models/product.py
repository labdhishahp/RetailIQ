from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    category: Mapped["Category"] = relationship(back_populates="products")
    inventory_records: Mapped[list["Inventory"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    sale_items: Mapped[list["SaleItem"]] = relationship(back_populates="product")


from app.models.category import Category  # noqa: E402
from app.models.inventory import Inventory  # noqa: E402
from app.models.sale_item import SaleItem  # noqa: E402
