"""Pytest fixtures for async testing of HMS backend."""

import asyncio
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport

from app.core.config import get_settings
from app.main import app

settings = get_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for test session."""
    # pyrefly: ignore[deprecated]
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    # pyrefly: ignore[bad-argument-type]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_client(async_client: AsyncClient) -> AsyncClient:
    """Async HTTP test client authenticated as Super Admin."""
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hms.local", "password": "Admin@123"},
    )
    if res.status_code == 200:
        token = res.json()["access_token"]
        async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client
