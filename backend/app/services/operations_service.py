"""Write operations: catalogue changes, stock movements, sales and reorders.

Every stock change goes through record_movement so the ledger and the on-hand
quantity stay consistent, and all multi-row writes share one transaction.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Category, Inventory, Product, PurchaseOrder, Sale, SaleItem, StockMovement, Store,
)
from app.services.cache import invalidate

logger = logging.getLogger(__name__)


class OperationsError(ValueError):
    """Raised for domain rule violations (surfaced as HTTP 400)."""


class OperationsService:
    # -- catalogue -------------------------------------------------------

    @staticmethod
    def _flush_cache() -> None:
        invalidate()

    def create_product(self, db: Session, data: dict) -> Product:
        if db.scalar(select(Product).where(Product.sku == data["sku"])):
            raise OperationsError(f"SKU {data['sku']} already exists")
        if not db.get(Category, data["category_id"]):
            raise OperationsError("Unknown category")
        product = Product(**data)
        db.add(product)
        db.commit()
        db.refresh(product)
        self._flush_cache()
        return product

    def update_product(self, db: Session, product_id: int, data: dict) -> Product:
        product = db.get(Product, product_id)
        if not product:
            raise OperationsError("Product not found")
        for key, value in data.items():
            if value is not None:
                setattr(product, key, value)
        db.commit()
        db.refresh(product)
        self._flush_cache()
        return product

    def delete_product(self, db: Session, product_id: int) -> None:
        product = db.get(Product, product_id)
        if not product:
            raise OperationsError("Product not found")
        sold = db.scalar(
            select(func.count()).select_from(SaleItem).where(SaleItem.product_id == product_id))
        if sold:
            raise OperationsError(
                f"Cannot delete {product.sku}: it appears on {sold} sale line(s). "
                "Set its status to discontinued instead.")
        db.delete(product)
        db.commit()
        self._flush_cache()

    # -- stock -----------------------------------------------------------

    def record_movement(
        self, db: Session, *, product_id: int, store_id: int, quantity: int,
        movement_type: str, reference: str | None = None, note: str | None = None,
        commit: bool = True,
    ) -> StockMovement:
        inv = db.scalar(
            select(Inventory).where(
                Inventory.product_id == product_id, Inventory.store_id == store_id))
        if not inv:
            if quantity < 0:
                raise OperationsError("No inventory record for this product at this store")
            inv = Inventory(product_id=product_id, store_id=store_id, quantity_on_hand=0,
                            reorder_level=0, reorder_quantity=0)
            db.add(inv)
            db.flush()

        new_balance = inv.quantity_on_hand + quantity
        if new_balance < 0:
            raise OperationsError(
                f"Insufficient stock: {inv.quantity_on_hand} on hand, {abs(quantity)} requested")
        inv.quantity_on_hand = new_balance

        movement = StockMovement(
            product_id=product_id, store_id=store_id, movement_type=movement_type,
            quantity=quantity, balance_after=new_balance, reference=reference, note=note,
        )
        db.add(movement)
        self._refresh_status(db, product_id)
        if commit:
            db.commit()
            db.refresh(movement)
            self._flush_cache()
        return movement

    def _refresh_status(self, db: Session, product_id: int) -> None:
        """Keep product.status consistent with its aggregate stock position."""
        row = db.execute(
            select(func.coalesce(func.sum(Inventory.quantity_on_hand), 0),
                   func.coalesce(func.sum(Inventory.reorder_level), 0))
            .where(Inventory.product_id == product_id)
        ).one()
        qty, level = int(row[0]), int(row[1])
        product = db.get(Product, product_id)
        if not product or product.status == "discontinued":
            return
        if qty == 0:
            product.status = "out_of_stock"
        elif level and qty <= level:
            product.status = "low_stock"
        elif level and qty > level * 2:
            product.status = "overstock"
        else:
            product.status = "active"

    def update_inventory_settings(
        self, db: Session, inventory_id: int, *,
        reorder_level: int | None = None, reorder_quantity: int | None = None,
        warehouse_name: str | None = None,
    ) -> Inventory:
        inv = db.get(Inventory, inventory_id)
        if not inv:
            raise OperationsError("Inventory record not found")
        if reorder_level is not None:
            inv.reorder_level = reorder_level
        if reorder_quantity is not None:
            inv.reorder_quantity = reorder_quantity
        if warehouse_name is not None:
            inv.warehouse_name = warehouse_name
        self._refresh_status(db, inv.product_id)
        db.commit()
        db.refresh(inv)
        self._flush_cache()
        return inv

    # -- sales -----------------------------------------------------------

    def create_sale(
        self, db: Session, *, store_id: int, items: list[dict],
        customer_id: int | None = None,
    ) -> Sale:
        """Create a sale and decrement stock atomically."""
        if not items:
            raise OperationsError("A sale needs at least one line item")
        if not db.get(Store, store_id):
            raise OperationsError("Unknown store")

        now = datetime.now(timezone.utc)
        key = now.strftime("%Y%m%d")
        seq = db.scalar(
            select(func.count()).select_from(Sale)
            .where(Sale.sale_number.like(f"SALE-{key}-%"))) or 0
        sale = Sale(store_id=store_id, customer_id=customer_id,
                    sale_number=f"SALE-{key}-{seq + 1:04d}", sale_date=now,
                    total_amount=Decimal("0.00"), total_items=0, status="completed")
        db.add(sale)
        db.flush()

        total, count = Decimal("0.00"), 0
        try:
            for line in items:
                product = db.get(Product, line["product_id"])
                if not product:
                    raise OperationsError(f"Unknown product {line['product_id']}")
                qty = int(line["quantity"])
                if qty <= 0:
                    raise OperationsError("Quantity must be positive")
                unit_price = Decimal(str(line.get("unit_price") or product.price))
                line_total = (unit_price * qty).quantize(Decimal("0.01"))
                db.add(SaleItem(
                    sale_id=sale.id, product_id=product.id, quantity=qty,
                    unit_price=unit_price, unit_cost=product.cost, line_total=line_total))
                self.record_movement(
                    db, product_id=product.id, store_id=store_id, quantity=-qty,
                    movement_type="sale", reference=sale.sale_number, commit=False)
                total += line_total
                count += qty

            sale.total_amount, sale.total_items = total, count
            if customer_id:
                self._roll_customer(db, customer_id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(sale)
        self._flush_cache()
        return sale

    def _roll_customer(self, db: Session, customer_id: int) -> None:
        from app.models import Customer
        customer = db.get(Customer, customer_id)
        if not customer:
            return
        row = db.execute(
            select(func.count(), func.coalesce(func.sum(Sale.total_amount), 0),
                   func.max(Sale.sale_date))
            .where(Sale.customer_id == customer_id)
        ).one()
        customer.total_orders = int(row[0] or 0)
        customer.total_spent = row[1] or Decimal("0.00")
        customer.last_order_date = row[2].date() if row[2] else None
        customer.status = "active"

    # -- reorders --------------------------------------------------------

    def create_purchase_order(
        self, db: Session, *, product_id: int, store_id: int, quantity: int,
        user_id: int | None = None, note: str | None = None,
    ) -> PurchaseOrder:
        product = db.get(Product, product_id)
        if not product:
            raise OperationsError("Unknown product")
        if quantity <= 0:
            raise OperationsError("Quantity must be positive")
        count = db.scalar(select(func.count()).select_from(PurchaseOrder)) or 0
        po = PurchaseOrder(
            reference=f"PO-{count + 1:05d}", product_id=product_id, store_id=store_id,
            quantity=quantity, unit_cost=product.cost,
            total_cost=(product.cost * quantity).quantize(Decimal("0.01")),
            status="placed", supplier=product.supplier, created_by_id=user_id, note=note,
        )
        db.add(po)
        db.commit()
        db.refresh(po)
        self._flush_cache()
        return po

    def receive_purchase_order(self, db: Session, po_id: int) -> PurchaseOrder:
        po = db.get(PurchaseOrder, po_id)
        if not po:
            raise OperationsError("Purchase order not found")
        if po.status == "received":
            raise OperationsError("Purchase order already received")
        if po.status == "cancelled":
            raise OperationsError("Cannot receive a cancelled purchase order")
        self.record_movement(
            db, product_id=po.product_id, store_id=po.store_id, quantity=po.quantity,
            movement_type="restock", reference=po.reference, commit=False)
        po.status = "received"
        db.commit()
        db.refresh(po)
        self._flush_cache()
        return po


operations_service = OperationsService()
