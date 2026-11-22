"""Exercise valid onboarding and tenant list authorization through HTTP routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.tenants import router
from app.core.database import get_db
from app.core.security import get_current_user, verify_password
from app.models.tenant import Hospital


@pytest.fixture
def tenant_client(monkeypatch):
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    added = []

    def add(row):
        row.id = str(uuid4())
        added.append(row)

    db.add.side_effect = add
    audit = SimpleNamespace(log=AsyncMock())
    monkeypatch.setattr("app.api.v1.tenants.get_audit_logger", AsyncMock(return_value=audit))
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    for route in router.routes:
        for dependency in route.dependencies:
            app.dependency_overrides[dependency.dependency] = lambda: None
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {
        "role": "HOSPITAL_ADMIN", "hospital_id": "tenant-a"
    }
    with TestClient(app) as client:
        yield client, db, added, audit, app


def test_successful_hospital_signup(tenant_client):
    client, db, added, audit, _ = tenant_client
    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
    db.execute.return_value = empty
    response = client.post("/api/v1/tenants/register", json={
        "hospital_name": "Test Hospital", "hospital_code": "TEST_HOSPITAL",
        "admin_name": "Hospital Admin", "admin_email": "admin@example.com",
        "admin_password": "StrongPassword123!",
    })
    assert response.status_code == 201, response.text
    hospital, admin = added
    assert admin.full_name == "Hospital Admin"
    assert admin.hospital_id == hospital.id
    assert admin.role == "HOSPITAL_ADMIN"
    assert verify_password("StrongPassword123!", admin.hashed_password)
    assert response.json()["hospital_id"] == hospital.id
    audit.log.assert_awaited_once()
    assert "hashed_password" not in response.text


@pytest.mark.parametrize("role,hospital_id,expected", [
    ("HOSPITAL_ADMIN", "tenant-a", 200),
    ("DOCTOR", None, 403),
    ("SUPER_ADMIN", None, 200),
])
def test_tenant_list_scope(tenant_client, role, hospital_id, expected):
    client, db, _, _, app = tenant_client
    app.dependency_overrides[get_current_user] = lambda: {
        "role": role, "hospital_id": hospital_id
    }
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    response = client.get("/api/v1/tenants/list")
    assert response.status_code == expected
    if expected == 403:
        db.execute.assert_not_awaited()
    elif role != "SUPER_ADMIN":
        query = db.execute.call_args.args[0]
        assert "tenant-a" in query.compile().params.values()
        assert "hospitals.id =" in str(query)


def test_anonymous_cannot_list_tenants(tenant_client):
    client, _, _, _, app = tenant_client
    del app.dependency_overrides[get_current_user]
    assert client.get("/api/v1/tenants/list").status_code == 401


def test_tenant_list_returns_only_own_hospital(tenant_client):
    client, db, _, _, app = tenant_client
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    table = Hospital.__table__.to_metadata(MetaData())
    for column in table.columns:
        column.server_default = None
    table.create(engine)
    first_id, second_id = str(uuid4()), str(uuid4())
    try:
        with Session(engine) as session:
            session.add_all([
                Hospital(id=first_id, name="First Hospital", code="first"),
                Hospital(id=second_id, name="Second Hospital", code="second"),
            ])
            session.commit()
            db.execute.side_effect = session.execute
            app.dependency_overrides[get_current_user] = lambda: {
                "role": "HOSPITAL_ADMIN", "hospital_id": first_id
            }
            response = client.get("/api/v1/tenants/list")
            assert response.status_code == 200
            assert [row["id"] for row in response.json()] == [first_id]
            app.dependency_overrides[get_current_user] = lambda: {
                "role": "SUPER_ADMIN", "hospital_id": first_id
            }
            response = client.get("/api/v1/tenants/list")
            assert {row["id"] for row in response.json()} == {first_id, second_id}
    finally:
        engine.dispose()
