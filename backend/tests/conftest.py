"""Pytest fixtures for async testing of HMS backend."""

import os
from collections.abc import AsyncGenerator
from typing import Any, cast

import pytest
from app.core.config import get_settings
from app.core.database import engine
from app.main import app
from httpx import ASGITransport, AsyncClient

settings = get_settings()


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    from app.core import dependencies, redis_state, security
    for module, attribute in ((dependencies, "_redis_pool"),
                              (redis_state, "_client"), (security, "_redis_pool")):
        client = getattr(module, attribute)
        if client is not None:
            await client.aclose()
            setattr(module, attribute, None)
    await engine.dispose()


@pytest.fixture(autouse=True)
def isolate_test_rate_limits():
    """Clear rate buckets only on the explicitly configured isolated test Redis."""
    if os.environ.get("STAGE1_OWNER_URL"):
        from urllib.parse import urlsplit
        if urlsplit(settings.REDIS_URL).hostname not in {"localhost", "127.0.0.1"}:
            raise RuntimeError("Stage 1 tests require an isolated local Redis instance")
        from redis import Redis
        with Redis.from_url(settings.REDIS_URL) as state:
            for key in state.scan_iter(match="rl:*"):
                state.delete(key)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    # pyrefly: ignore[bad-argument-type]
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_client(async_client: AsyncClient) -> AsyncClient:
    """Async HTTP client authenticated through the production cookie flow."""
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hms.local", "password": "Admin@123"},
    )
    assert res.status_code == 200, res.text
    async_client.headers["X-CSRF-Token"] = async_client.cookies.get("csrf_token") or ""
    # httpx retains Set-Cookie values on the same client. Do not manufacture an
    # Authorization header: browser clients use HttpOnly access cookies.
    return async_client
