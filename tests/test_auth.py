from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.rate_limit import limiter


async def test_register_returns_user_without_password(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": " Jane@Example.com ", "full_name": " Jane ", "password": "s3cure-pass"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "jane@example.com"
    assert body["full_name"] == "Jane"
    assert "password" not in body and "hashed_password" not in body


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    payload = {"email": "jane@example.com", "full_name": "Jane", "password": "s3cure-pass"}
    await client.post("/api/v1/auth/register", json=payload)
    res = await client.post("/api/v1/auth/register", json={**payload, "email": "JANE@example.com"})
    assert res.status_code == 409


async def test_register_validates_input(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "full_name": "", "password": "short"},
    )
    assert res.status_code == 422
    fields = {err["loc"][-1] for err in res.json()["detail"]}
    assert {"email", "full_name", "password"} <= fields


async def test_login_and_me(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "jane@example.com"


async def test_login_rejects_bad_credentials(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    wrong_password = await client.post(
        "/api/v1/auth/token", data={"username": "jane@example.com", "password": "nope-nope"}
    )
    unknown_user = await client.post(
        "/api/v1/auth/token", data={"username": "ghost@example.com", "password": "nope-nope"}
    )
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


async def test_expired_token_is_rejected(client: AsyncClient) -> None:
    settings = get_settings()
    token = jwt.encode(
        {"sub": "1", "type": "access", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_token_signed_with_other_key_is_rejected(client: AsyncClient) -> None:
    token = jwt.encode({"sub": "1", "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)},
                       "x" * 40, algorithm="HS256")
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_login_is_rate_limited(client: AsyncClient) -> None:
    limiter.enabled = True
    limiter.reset()
    try:
        statuses = [
            (await client.post("/api/v1/auth/token", data={"username": "a@b.com", "password": "x" * 8})).status_code
            for _ in range(6)
        ]
    finally:
        limiter.enabled = False
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
