"""Pytest fixtures for async testing of HMS backend."""

import asyncio
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport

from app.core.config import get_settings
from app.core.database import engine
from app.main import app

settings = get_settings()


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await engine.dispose()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    # pyrefly: ignore[bad-argument-type]
    transport = ASGITransport(app=app)
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
    # httpx retains Set-Cookie values on the same client. Do not manufacture an
    # Authorization header: browser clients use HttpOnly access cookies.
    return async_client
