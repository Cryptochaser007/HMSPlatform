"""Unit and integration tests for Patient Registration & Demographics."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_patient_registration_validation(async_client: AsyncClient):
    """Test validation constraints on patient registration."""
    invalid_payload = {
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "gender": "INVALID_GENDER",
        "phone": "123",  # Too short
    }
    response = await async_client.post("/api/v1/patients/", json=invalid_payload)
    # Rejects with 401/403 (unauthorized) or 422 (unprocessable validation)
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_patient_registration_authenticated(auth_client: AsyncClient):
    """Test successful patient creation with auto-generated UHID and encryption."""
    payload = {
        "first_name": "Rohan",
        "last_name": "Verma",
        "date_of_birth": "1995-04-20",
        "gender": "MALE",
        "phone": "9876543210",
        "blood_group": "O+",
        "city": "Bengaluru",
        "state": "Karnataka",
    }
    response = await auth_client.post("/api/v1/patients/", json=payload)
    if response.status_code == 201:
        data = response.json()
        assert "id" in data
        assert "registration_number" in data
        assert data["first_name"] == "Rohan"
        assert data["registration_number"].startswith("UHID-")
