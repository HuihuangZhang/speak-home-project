"""Integration tests: auth endpoints + real in-memory SQLite."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_success(client, user_payload):
    resp = await client.post("/auth/register", json=user_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_register_duplicate_email(client, user_payload):
    await client.post("/auth/register", json=user_payload)
    resp = await client.post("/auth/register", json=user_payload)
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


async def test_register_invalid_email(client):
    resp = await client.post("/auth/register", json={"email": "not-an-email", "password": "pass12345"})
    assert resp.status_code == 422


async def test_register_weak_password(client):
    resp = await client.post("/auth/register", json={"email": "a@b.com", "password": "123"})
    assert resp.status_code == 422


async def test_login_success(client, user_payload):
    await client.post("/auth/register", json=user_payload)
    resp = await client.post("/auth/login", json=user_payload)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client, user_payload):
    await client.post("/auth/register", json=user_payload)
    resp = await client.post("/auth/login", json={"email": user_payload["email"], "password": "WRONG"})
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    resp = await client.post("/auth/login", json={"email": "ghost@example.com", "password": "x"})
    assert resp.status_code == 401


async def test_protected_endpoint_requires_auth(client):
    resp = await client.get("/sessions")
    assert resp.status_code == 401


async def test_protected_endpoint_with_invalid_token(client):
    resp = await client.get("/sessions", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code == 401
