from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), default="Email", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
