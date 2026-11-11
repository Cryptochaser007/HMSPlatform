"""Unit and integration tests for authentication and user access."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test public health endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient):
    """Ensure protected routes reject requests missing Bearer tokens."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 403 or response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_login(async_client: AsyncClient):
    """Test login failure with invalid credentials."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@hms.local", "password": "WrongPassword123"},
    )
    assert response.status_code == 401

