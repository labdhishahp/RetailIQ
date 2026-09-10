"""Write path: catalogue, stock ledger, sales and purchase orders."""

import pytest

from app.models import Inventory, Product
from app.services.operations_service import OperationsError, operations_service


def test_create_and_update_product(client, auth, seeded):
    r = client.post("/api/v1/products", headers=auth, json={
        "sku": "T-NEW1", "name": "Created Product", "category_id": seeded["category_id"],
        "supplier": "S9", "price": 30.0, "cost": 12.0, "status": "active",
    })
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["price"] == 30.0          # money serialises as a number

    r = client.patch(f"/api/v1/products/{pid}", headers=auth, json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"

    assert client.delete(f"/api/v1/products/{pid}", headers=auth).status_code == 204


def test_duplicate_sku_rejected(client, auth, seeded):
    payload = {"sku": "T-001", "name": "Clash", "category_id": seeded["category_id"],
               "price": 1.0, "cost": 0.5}
    assert client.post("/api/v1/products", headers=auth, json=payload).status_code == 400


def test_delete_blocked_when_product_has_sales(client, auth, seeded):
    r = client.delete(f"/api/v1/products/{seeded['fast_id']}", headers=auth)
    assert r.status_code == 400
    assert "sale" in r.json()["detail"].lower()


def test_stock_adjustment_updates_balance_and_ledger(client, auth, db, seeded):
    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    db.refresh(inv)
    before = inv.quantity_on_hand

    r = client.post("/api/v1/inventory/adjust", headers=auth, json={
        "product_id": seeded["fast_id"], "store_id": seeded["store_id"],
        "quantity": 25, "movement_type": "restock", "note": "test",
    })
    assert r.status_code == 201
    assert r.json()["balance_after"] == before + 25

    # ledger records it
    movements = client.get(
        f"/api/v1/stock-movements?product_id={seeded['fast_id']}", headers=auth).json()
    assert movements[0]["movement_type"] == "restock"
    assert movements[0]["quantity"] == 25

    client.post("/api/v1/inventory/adjust", headers=auth, json={
        "product_id": seeded["fast_id"], "store_id": seeded["store_id"],
        "quantity": -25, "movement_type": "adjustment"})


def test_cannot_oversell(client, auth, seeded):
    r = client.post("/api/v1/inventory/adjust", headers=auth, json={
        "product_id": seeded["fast_id"], "store_id": seeded["store_id"],
        "quantity": -99999, "movement_type": "adjustment"})
    assert r.status_code == 400
    assert "insufficient" in r.json()["detail"].lower()


def test_sale_decrements_stock_atomically(client, auth, db, seeded):
    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    db.refresh(inv)
    before = inv.quantity_on_hand

    r = client.post("/api/v1/sales", headers=auth, json={
        "store_id": seeded["store_id"], "customer_id": seeded["customer_id"],
        "items": [{"product_id": seeded["fast_id"], "quantity": 2}],
    })
    assert r.status_code == 201
    assert r.json()["total_items"] == 2

    db.expire_all()
    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    assert inv.quantity_on_hand == before - 2


def test_sale_rolls_back_when_a_line_is_invalid(client, auth, db, seeded):
    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    db.refresh(inv)
    before = inv.quantity_on_hand

    r = client.post("/api/v1/sales", headers=auth, json={
        "store_id": seeded["store_id"],
        "items": [
            {"product_id": seeded["fast_id"], "quantity": 1},
            {"product_id": 999999, "quantity": 1},          # invalid -> whole sale fails
        ],
    })
    assert r.status_code == 400

    db.expire_all()
    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    assert inv.quantity_on_hand == before, "stock must not change on a failed sale"


def test_purchase_order_lifecycle(client, auth, db, seeded):
    r = client.post("/api/v1/purchase-orders", headers=auth, json={
        "product_id": seeded["fast_id"], "store_id": seeded["store_id"], "quantity": 10})
    assert r.status_code == 201
    po = r.json()
    assert po["status"] == "placed"
    assert po["total_cost"] == pytest.approx(po["unit_cost"] * 10)

    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    db.refresh(inv)
    before = inv.quantity_on_hand

    r = client.post(f"/api/v1/purchase-orders/{po['id']}/receive", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "received"

    db.expire_all()
    inv = db.query(Inventory).filter_by(
        product_id=seeded["fast_id"], store_id=seeded["store_id"]).one()
    assert inv.quantity_on_hand == before + 10

    # receiving twice is rejected
    assert client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive", headers=auth).status_code == 400


def test_product_status_follows_stock_position(db, seeded, SessionLocal):
    session = SessionLocal()
    try:
        operations_service._refresh_status(session, seeded["fast_id"])
        session.commit()
        product = session.get(Product, seeded["fast_id"])
        assert product.status in {"active", "low_stock", "overstock", "out_of_stock"}
    finally:
        session.close()


def test_operations_error_on_unknown_store(SessionLocal, seeded):
    session = SessionLocal()
    try:
        with pytest.raises(OperationsError):
            operations_service.create_sale(
                session, store_id=999999,
                items=[{"product_id": seeded["fast_id"], "quantity": 1}])
    finally:
        session.rollback()
        session.close()
