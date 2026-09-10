from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerRead


class CustomerService:
    """Read operations for customer records."""

    def list_customers(self, db: Session, *, skip: int = 0, limit: int = 200) -> list[CustomerRead]:
        rows = db.scalars(
            select(Customer).order_by(Customer.total_spent.desc()).offset(skip).limit(limit)
        ).all()
        return [CustomerRead.model_validate(r) for r in rows]

    def get_customer(self, db: Session, customer_id: int) -> CustomerRead | None:
        row = db.get(Customer, customer_id)
        return CustomerRead.model_validate(row) if row else None


customer_service = CustomerService()
