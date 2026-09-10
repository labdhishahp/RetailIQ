"""Authentication, authorisation and password handling."""

import pytest

from app.core.security import create_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    stored = hash_password("Correct horse battery")
    assert stored != "Correct horse battery"
    assert verify_password("Correct horse battery", stored)
    assert not verify_password("wrong", stored)


def test_password_hash_is_salted():
    assert hash_password("same") != hash_password("same")


def test_verify_rejects_malformed_hash():
    assert not verify_password("x", "not-a-hash")


def test_login_success(client, seeded):
    r = client.post("/api/v1/auth/login",
                    json={"email": "t-admin@retailiq-test.com", "password": "TestPass123!"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_login_wrong_password(client, seeded):
    r = client.post("/api/v1/auth/login",
                    json={"email": "t-admin@retailiq-test.com", "password": "nope"})
    assert r.status_code == 401


def test_login_unknown_user(client, seeded):
    r = client.post("/api/v1/auth/login",
                    json={"email": "ghost@retailiq-test.com", "password": "TestPass123!"})
    assert r.status_code == 401


@pytest.mark.parametrize("path", [
    "/api/v1/products", "/api/v1/analytics/kpis", "/api/v1/recommendations",
    "/api/v1/alerts", "/api/v1/copilot/documents",
])
def test_endpoints_require_auth(client, path):
    assert client.get(path).status_code == 401


def test_rejects_garbage_token(client):
    r = client.get("/api/v1/products", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_access(client, seeded):
    tokens = client.post("/api/v1/auth/login",
                         json={"email": "t-admin@retailiq-test.com", "password": "TestPass123!"}).json()
    r = client.get("/api/v1/products",
                   headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401


def test_expired_token_rejected(client, seeded):
    expired = create_access_token(subject="t-admin@retailiq-test.com", role="admin", expires_minutes=-1)
    r = client.get("/api/v1/products", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_me_returns_current_user(client, auth):
    r = client.get("/api/v1/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["email"] == "t-admin@retailiq-test.com"
    assert "hashed_password" not in r.json()


def test_analyst_cannot_write(client, analyst_token, seeded):
    r = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"sku": "T-BLOCK", "name": "Blocked", "category_id": seeded["category_id"],
              "price": 1, "cost": 1},
    )
    assert r.status_code == 403


def test_analyst_can_read(client, analyst_token):
    r = client.get("/api/v1/products", headers={"Authorization": f"Bearer {analyst_token}"})
    assert r.status_code == 200
