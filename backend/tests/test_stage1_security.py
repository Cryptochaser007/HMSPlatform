"""Stage 1 functional tests against a dedicated PostgreSQL runtime role and Redis.

Set STAGE1_OWNER_URL to an isolated test database owner URL. DATABASE_URL must
point at the same database using a NOSUPERUSER NOBYPASSRLS runtime account.
"""
import asyncio
import base64
import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from app.core.encryption import FieldEncryptor
from app.core.security import is_token_blacklisted
from app.main import app
from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

OWNER_URL = os.environ.get("STAGE1_OWNER_URL")
DATABASE_TEST = pytest.mark.skipif(not OWNER_URL, reason="Dedicated Stage 1 PostgreSQL test database required")


def test_production_docs_are_disabled():
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, "-c",
        ("from app.main import app; assert app.docs_url is None; "
         "assert app.redoc_url is None; assert app.openapi_url is None"),
    ], check=False, env={**os.environ, "ENVIRONMENT": "production"}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_redis_tls_uses_ssl_connection():
    from redis.asyncio import Redis
    from redis.asyncio.connection import SSLConnection
    client = Redis.from_url("rediss://default:test@redis.example.com:6379")
    assert client.connection_pool.connection_class is SSLConnection


def test_cached_timeline_is_tenant_scoped():
    from app.abdm.hiu_service import _longitudinal_records, hiu_service
    from app.core.tenant_context import current_hospital, tenant_cache_key
    first = current_hospital.set({"hospital_id": "hospital-a"})
    key = tenant_cache_key("patient@sbx")
    try:
        _longitudinal_records[key] = [{"bundle_id": "private"}]
        assert hiu_service.get_longitudinal_records("patient@sbx") == [{"bundle_id": "private"}]
        current_hospital.set({"hospital_id": "hospital-b"})
        assert hiu_service.get_longitudinal_records("patient@sbx") == []
    finally:
        _longitudinal_records.pop(key, None)
        current_hospital.reset(first)


def test_stage1_ciphertext_and_legacy_readers():
    key = Fernet.generate_key().decode()
    cipher = FieldEncryptor(key=key)
    token = cipher.encrypt("patient record")
    version, nonce, payload = token.split(":")
    assert version == "v1"
    assert len(base64.b64decode(nonce)) == 12
    assert len(base64.b64decode(payload)) > 16
    assert token != cipher.encrypt("patient record")
    assert cipher.decrypt(token) == "patient record"
    legacy = Fernet(key.encode()).encrypt(b"old record").decode()
    assert cipher.decrypt(legacy) == "old record"
    damaged = bytearray(base64.b64decode(payload))
    damaged[0] ^= 1
    with pytest.raises(InvalidTag):
        cipher.decrypt(f"v1:{nonce}:{base64.b64encode(damaged).decode()}")


@pytest.mark.asyncio
async def test_revocation_fails_closed(monkeypatch):
    from unittest.mock import AsyncMock
    monkeypatch.setattr("app.core.security._get_redis", AsyncMock(return_value=None))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as failure:
        await is_token_blacklisted("unrevoked-token")
    assert failure.value.status_code == 503


@pytest.mark.asyncio
async def test_trial_uses_mock_even_when_host_has_sandbox_credentials(monkeypatch):
    from unittest.mock import AsyncMock

    from app.abdm.client import ABDMClient
    from app.abdm.config import ABDMMode, ABDMSettings
    from app.core.tenant_context import current_hospital
    client = ABDMClient(ABDMSettings(abdm_env=ABDMMode.SANDBOX))
    monkeypatch.setattr(client, "record_transaction", AsyncMock())
    live_call = AsyncMock(side_effect=AssertionError("Trial attempted a live NHA request"))
    monkeypatch.setattr(client._adapter, "request", live_call)
    context = current_hospital.set({"hospital_id": str(uuid4()), "abdm_env": "MOCK"})
    try:
        result = await client._make_request("POST", "/enrollment/request/otp", target="abha")
        assert result["abdm_mode"] == "MOCK"
        live_call.assert_not_awaited()
    finally:
        current_hospital.reset(context)
        await client.close()


@pytest.mark.asyncio
async def test_csp_localhost_only_in_development(monkeypatch):
    from app.core.config import get_settings
    from app.core.wasa_security import SecurityHeadersMiddleware
    from fastapi import FastAPI
    local_app = FastAPI()
    local_app.add_middleware(SecurityHeadersMiddleware)
    @local_app.get("/")
    async def root():
        return {"status": "ok"}
    async with AsyncClient(transport=ASGITransport(app=local_app), base_url="https://test") as client:
        for environment in ("development", "production"):
            monkeypatch.setattr(get_settings(), "ENVIRONMENT", environment)
            response = await client.get("/")
            assert ("http://localhost:*" in response.headers["content-security-policy"]) == (environment == "development")


async def signup(client, prefix):
    slug = f"{prefix}-{uuid4().hex[:12]}"
    payload = {"hospital_name": f"{prefix} Hospital", "slug": slug,
               "admin_name": "Hospital Administrator", "admin_email": f"{slug}@example.com",
               "admin_password": "Stage1StrongPassword!"}
    response = await client.post("/api/v1/tenants/register", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["abdm_env"] == "MOCK"
    response = await client.post("/api/v1/auth/login", json={
        "email": payload["admin_email"], "password": payload["admin_password"]
    })
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    return response, payload


@DATABASE_TEST
@pytest.mark.asyncio
async def test_ward_setup_skip_and_inventory_are_tenant_scoped():
    transport = ASGITransport(app=app)
    setup = "/api/v1/wards/setup"
    occupancy = "/api/v1/wards/occupancy"
    async with (
        AsyncClient(transport=transport, base_url="https://test") as hospital,
        AsyncClient(transport=transport, base_url="https://test") as clinic,
        AsyncClient(transport=transport, base_url="https://test") as fresh_session,
        AsyncClient(transport=transport, base_url="https://test") as doctor,
    ):
        assert (await fresh_session.get(setup)).status_code == 401
        await signup(hospital, "bed-setup-hospital")
        _, clinic_credentials = await signup(clinic, "bed-setup-clinic")
        assert (await hospital.get(setup)).json() == {"status": "pending"}
        assert (await clinic.get(setup)).json() == {"status": "pending"}

        skipped = await clinic.post(setup, json={"mode": "OPD_ONLY"})
        assert skipped.status_code == 200, skipped.text
        assert skipped.json() == {"status": "skipped"}
        login = await fresh_session.post("/api/v1/auth/login", json={
            "email": clinic_credentials["admin_email"], "password": clinic_credentials["admin_password"],
        })
        assert login.status_code == 200, login.text
        fresh_session.headers["X-CSRF-Token"] = fresh_session.cookies.get("csrf_token") or ""
        assert (await fresh_session.get(setup)).json() == {"status": "skipped"}
        assert (await hospital.get(setup)).json() == {"status": "pending"}

        wards = [
            {"name": "General East", "ward_type": "GENERAL", "floor": 1, "total_beds": 14},
            {"name": "ICU East", "ward_type": "ICU", "floor": 2, "total_beds": 4},
            {"name": "NICU East", "ward_type": "NICU", "floor": 2, "total_beds": 2},
        ]
        payload = {"mode": "INPATIENT", "wards": wards}
        invalid = await hospital.post(setup, json={**payload, "wards": [wards[0], wards[0]]})
        assert invalid.status_code == 422
        assert (await hospital.get(occupancy)).json()["total_beds"] == 0
        foreign = await hospital.post(setup, json={**payload, "hospital_id": str(uuid4())})
        assert foreign.status_code == 422

        first, retry = await asyncio.gather(
            hospital.post(setup, json=payload), hospital.post(setup, json=payload),
        )
        for response in (first, retry):
            assert response.status_code == 200, response.text
            assert response.json() == {"status": "configured"}
        assert (await hospital.get(setup)).json() == {"status": "configured"}
        saved = (await hospital.get(occupancy)).json()
        assert saved["total_beds"] == saved["available"] == 20
        assert {row["ward_type"]: len(row["beds"]) for row in saved["wards"]} == {
            "GENERAL": 14, "ICU": 4, "NICU": 2,
        }
        clinic_inventory = await fresh_session.get(occupancy)
        assert clinic_inventory.status_code == 200, clinic_inventory.text
        assert clinic_inventory.json()["total_beds"] == 0
        assert (await hospital.post(setup, json={"mode": "OPD_ONLY"})).status_code == 409
        assert (await hospital.post(setup, json={**payload, "wards": wards[:1]})).status_code == 409

        resumed = await fresh_session.post(setup, json={**payload, "wards": wards[2:]})
        assert resumed.status_code == 200, resumed.text
        assert resumed.json() == {"status": "configured"}
        assert (await fresh_session.get(setup)).json() == {"status": "configured"}
        assert (await fresh_session.get(occupancy)).json()["total_beds"] == 2

        email = f"ward-doctor-{uuid4().hex}@example.com"
        credentials = {"email": email, "password": "Stage1StrongPassword!"}
        created = await hospital.post("/api/v1/auth/signup", json={
            **credentials, "full_name": "Ward Test Doctor", "role": "DOCTOR",
        })
        assert created.status_code == 201, created.text
        doctor_login = await doctor.post("/api/v1/auth/login", json=credentials)
        assert doctor_login.status_code == 200, doctor_login.text
        doctor.headers["X-CSRF-Token"] = doctor.cookies.get("csrf_token") or ""
        assert (await doctor.get(setup)).status_code == 403
        assert (await doctor.post(setup, json=payload)).status_code == 403


@DATABASE_TEST
@pytest.mark.asyncio
async def test_bed_inventory_is_empty_then_tenant_scoped():
    transport = ASGITransport(app=app)
    occupancy_url = "/api/v1/wards/occupancy"
    async with AsyncClient(transport=transport, base_url="https://test") as first, AsyncClient(
        transport=transport, base_url="https://test"
    ) as second:
        await signup(first, "ward-a")
        await signup(second, "ward-b")

        async def get_inventory(client):
            response = await client.get(occupancy_url)
            assert response.status_code == 200, response.text
            return response.json()

        async def create_ward(client, name, ward_type, count):
            response = await client.post("/api/v1/wards/", json={
                "name": name, "ward_type": ward_type, "floor": 1, "total_beds": count,
            })
            assert response.status_code == 201, response.text
            return response.json()["id"]

        blank = await get_inventory(first)
        assert blank == {
            "total_beds": 0, "occupied": 0, "available": 0, "maintenance": 0, "reserved": 0,
            "occupancy_rate": 0.0, "by_ward_type": [], "wards": [],
        }

        first_icu = await create_ward(first, "ICU East", "ICU", 2)
        first_nicu = await create_ward(first, "NICU East", "NICU", 1)
        assert await get_inventory(second) == blank
        second_general = await create_ward(second, "General West", "GENERAL", 4)

        first_inventory = await get_inventory(first)
        assert first_inventory["total_beds"] == first_inventory["available"] == 3
        wards = {ward["id"]: ward for ward in first_inventory["wards"]}
        assert wards.keys() == {first_icu, first_nicu}
        assert wards[first_nicu]["ward_type"] == "NICU"
        icu_beds = wards[first_icu]["beds"]
        assert [bed["bed_number"] for bed in icu_beds] == ["ICU-101", "ICU-102"]
        bed_id = icu_beds[0]["id"]
        assert set(icu_beds[0]) == {"id", "bed_number", "status"}
        bed_status_url = f"/api/v1/wards/beds/{bed_id}/status"
        blocked = await second.put(bed_status_url, json={"status": "MAINTENANCE"})
        assert blocked.status_code == 404, blocked.text
        changed = await first.put(bed_status_url, json={"status": "MAINTENANCE"})
        assert changed.status_code == 200, changed.text
        updated = await get_inventory(first)
        assert (updated["total_beds"], updated["available"], updated["maintenance"]) == (3, 2, 1)
        assert updated["wards"][0]["beds"][0] == {
            "id": bed_id, "bed_number": "ICU-101", "status": "MAINTENANCE",
        }
        assert updated["by_ward_type"][0]["available"] == 1

        second_inventory = await get_inventory(second)
        assert second_inventory["total_beds"] == second_inventory["available"] == 4
        assert [ward["id"] for ward in second_inventory["wards"]] == [second_general]
        assert bed_id not in {bed["id"] for bed in second_inventory["wards"][0]["beds"]}


@pytest.mark.asyncio
async def test_abdm_routes_fail_closed_when_disabled(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "ABDM_ENABLED", False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        status = await client.get("/api/v1/abdm/status")
        assert status.status_code == 200
        assert status.json()["integration_enabled"] is False
        for method, path in [
            ("POST", "/api/v1/abdm/abha/aadhaar/otp"),
            ("POST", "/api/v1/abdm/abha/link-patient"),
            ("POST", "/api/v1/abdm/hiu/health-info/fetch"),
            ("GET", "/api/v1/abdm/hiu/records/pilot@example"),
            ("POST", "/api/v1/registry/hfr/sync"),
            ("POST", "/api/v3/hip/patient/care-context/discover"),
            ("POST", "/api/v1/abdm/v3/hip/patient/care-context/discover"),
        ]:
            response = await client.request(method, path)
            assert response.status_code == 403, (path, response.text)
            assert response.json()["detail"] == "ABHA integration is unavailable in this environment."


@DATABASE_TEST
@pytest.mark.asyncio
async def test_signup_isolation_idle_lockout_and_audit(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "ABDM_ENABLED", False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as first, AsyncClient(
        transport=transport, base_url="https://test"
    ) as second:
        login, _credentials = await signup(first, "first")
        _, other_credentials = await signup(second, "second")
        assert "HttpOnly" in login.headers.get_list("set-cookie")[0]
        profile = await first.get("/api/v1/auth/me")
        assert profile.status_code == 200, profile.text
        patient = {"first_name": "Private", "last_name": "Patient", "date_of_birth": "1990-01-01",
                   "gender": "MALE", "phone": "9876543210"}
        assert (await first.post("/api/v1/patients/", json={**patient, "abha_id": "12345678901234"})).status_code == 403
        created = await first.post("/api/v1/patients/", json=patient)
        assert created.status_code == 201, created.text
        patient_id = created.json()["id"]
        assert (await first.put(f"/api/v1/patients/{patient_id}", json={"abha_address": "test@abdm"})).status_code == 403
        assert (await second.get(f"/api/v1/patients/{patient_id}")).status_code == 404
        assert (await second.put(f"/api/v1/patients/{patient_id}", json={"city": "Other"})).status_code == 404
        listing = await second.get("/api/v1/patients/")
        assert patient_id not in str(listing.json())
        from app.core.security import decode_token, security_redis
        claims = decode_token(first.cookies.get("access_token"))
        other_claims = decode_token(second.cookies.get("access_token"))
        assert claims["hospital_id"] != other_claims["hospital_id"]
        owner = await asyncpg.connect(OWNER_URL)
        try:
            assert await owner.fetchval("SELECT count(*) FROM departments WHERE hospital_id=$1::uuid",
                                        claims["hospital_id"]) == 1
            assert await owner.fetchval("SELECT count(*) FROM quality_indicators WHERE hospital_id=$1::uuid",
                                        claims["hospital_id"]) == 2
            assert await owner.fetchval("SELECT first_name FROM patients WHERE id=$1::uuid", patient_id) != "Private"
            # Attempt a cross-tenant child relationship through a real non-bypass role.
            runtime_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
            runtime = await asyncpg.connect(runtime_url)
            try:
                assert not await runtime.fetchval("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
                assert await runtime.fetchval("SELECT count(*) FROM patients") == 0
                async with runtime.transaction():
                    await runtime.execute("SELECT set_config('app.current_hospital_id',$1,true)", other_claims["hospital_id"])
                    with pytest.raises(asyncpg.InsufficientPrivilegeError):
                        async with runtime.transaction():
                            await runtime.execute(
                                "INSERT INTO departments(hospital_id,name) VALUES($1::uuid,'Forbidden')",
                                claims["hospital_id"],
                            )
                    with pytest.raises(asyncpg.ForeignKeyViolationError):
                        async with runtime.transaction():
                            await runtime.execute(
                                "INSERT INTO consents(patient_id,consent_type,purpose,data_categories,granted_to) "
                                "VALUES($1::uuid,'GENERAL','test','[]','test')", patient_id)
                assert await runtime.fetchval("SELECT count(*) FROM patients") == 0
            finally:
                await runtime.close()
            with pytest.raises(asyncpg.RaiseError):
                await owner.execute("UPDATE audit_logs SET entity_type='changed' WHERE user_id=$1::uuid", claims["sub"])
        finally:
            await owner.close()
        state = await security_redis()
        assert 0 < await state.ttl(f"auth:session:{claims['sub']}") <= 900
        await state.delete(f"auth:session:{claims['sub']}")
        assert (await first.get("/api/v1/auth/me")).status_code == 401
        assert (await first.post("/api/v1/auth/refresh")).status_code == 401
        for _ in range(5):
            response = await second.post("/api/v1/auth/login", json={
                "email": other_credentials["admin_email"], "password": "incorrect"
            })
            assert response.status_code == 401, response.text
            assert response.json()["detail"] == "Invalid username and/or password"
        response = await second.post("/api/v1/auth/login", json={
            "email": other_credentials["admin_email"], "password": other_credentials["admin_password"]
        })
        assert response.status_code == 401
        assert await state.get(f"auth:fail:{other_credentials['admin_email']}") == "5"
        from unittest.mock import AsyncMock
        monkeypatch.setattr("app.core.security._get_redis", AsyncMock(return_value=None))
        assert (await second.get("/api/v1/auth/me")).status_code == 503


@DATABASE_TEST
@pytest.mark.asyncio
async def test_opd_assigns_only_active_doctors_from_the_hospital():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as first, AsyncClient(
        transport=transport, base_url="https://test"
    ) as second:
        _, admin = await signup(first, "opd-first")
        await signup(second, "opd-second")
        directory = "/api/v1/encounters/assignable-doctors"
        assert (await first.get(directory)).json() == []

        async def create_doctor(client, name):
            response = await client.post("/api/v1/auth/signup", json={
                "email": f"doctor-{uuid4().hex}@example.com",
                "password": "Stage1StrongPassword!",
                "full_name": name,
                "role": "DOCTOR",
            })
            assert response.status_code == 201, response.text
            return response.json()["id"]

        doctor = await create_doctor(first, "OPD Doctor")
        other = await create_doctor(second, "Other Hospital Doctor")
        inactive = await create_doctor(first, "Inactive Doctor")
        owner = await asyncpg.connect(OWNER_URL)
        try:
            await owner.execute("UPDATE public.users SET is_active=false WHERE id=$1::uuid", inactive)
        finally:
            await owner.close()
        listed = await first.get(directory)
        assert listed.status_code == 200
        assert listed.json() == [{"id": doctor, "full_name": "OPD Doctor"}]

        patient = await first.post("/api/v1/patients/", json={
            "first_name": "Synthetic", "last_name": "Patient", "date_of_birth": "1990-01-01",
            "gender": "MALE", "phone": "9876543210",
        })
        assert patient.status_code == 201
        encounter = {
            "patient_id": patient.json()["id"], "department": "OPD", "encounter_type": "OPD",
        }
        admin_profile = await first.get("/api/v1/auth/me")
        assert admin_profile.json()["email"] == admin["admin_email"]
        for rejected in (other, inactive, admin_profile.json()["id"]):
            denied = await first.post("/api/v1/encounters/", json={**encounter, "doctor_id": rejected})
            assert denied.status_code == 404
        created = await first.post("/api/v1/encounters/", json={**encounter, "doctor_id": doctor})
        assert created.status_code == 201, created.text
        assert created.json()["doctor_id"] == doctor
        assert created.json()["token_number"] == 1


@DATABASE_TEST
@pytest.mark.asyncio
async def test_duplicate_signup_rolls_back_hospital():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        _, first = await signup(client, "duplicate")
        second_slug = f"duplicate-{uuid4().hex[:12]}"
        response = await client.post("/api/v1/tenants/register", json={
            **first, "slug": second_slug
        })
        assert response.status_code == 409, response.text
        owner = await asyncpg.connect(OWNER_URL)
        try:
            assert await owner.fetchval("SELECT count(*) FROM hospitals WHERE slug=$1", second_slug) == 0
        finally:
            await owner.close()


@DATABASE_TEST
@pytest.mark.asyncio
async def test_migration_can_be_reapplied_without_deleting_data():
    owner = await asyncpg.connect(OWNER_URL)
    try:
        before = await owner.fetchval("SELECT count(*) FROM users")
        migration = Path(__file__).parents[1] / "migrations/003_stage1_multitenancy_and_rls.sql"
        await owner.execute(migration.read_text(encoding="utf-8"))
        await owner.execute(migration.read_text(encoding="utf-8"))
        assert await owner.fetchval("SELECT count(*) FROM users") == before
        assert await owner.fetchval(
            "SELECT tgenabled='O' FROM pg_trigger WHERE tgname='trg_audit_logs_no_mutation'"
        )
    finally:
        await owner.close()


@DATABASE_TEST
@pytest.mark.asyncio
async def test_upgrade_from_prior_migrations_preserves_demo_and_encryption():
    from urllib.parse import urlsplit
    project = Path(__file__).parents[2]
    database_name = f"stage1_upgrade_{uuid4().hex}"
    owner = await asyncpg.connect(OWNER_URL)
    await owner.execute(f'CREATE DATABASE "{database_name}"')
    upgrade = None
    try:
        upgrade_url = urlsplit(OWNER_URL)._replace(path=f"/{database_name}").geturl()
        upgrade = await asyncpg.connect(upgrade_url)
        for file in ["scripts/supabase_schema.sql", "migrations/002_abdm_v3_exit_compliance.sql",
                     "scripts/supabase_seed.sql", "backend/migrations/003_aes256_rls_and_missing_modules.sql",
                     "backend/migrations/003_abdm_v3_and_ndhm_security_upgrade.sql"]:
            await upgrade.execute((project / file).read_text(encoding="utf-8"))
        cipher = FieldEncryptor(key="test-preserved-existing-secret")
        original = cipher.encrypt("Existing encrypted patient")
        await upgrade.execute(
            "INSERT INTO patients(registration_number,first_name,last_name,date_of_birth,gender,phone) "
            "VALUES('UPGRADE-TEST',$1,'record','1990-01-01','MALE','encrypted-phone')", original,
        )
        before = await upgrade.fetchval("SELECT count(*) FROM users")
        stage1 = (project / "backend/migrations/003_stage1_multitenancy_and_rls.sql").read_text(encoding="utf-8")
        await upgrade.execute(stage1)
        await upgrade.execute(stage1)
        assert await upgrade.fetchval("SELECT count(*) FROM users") == before
        stored = await upgrade.fetchval("SELECT first_name FROM patients WHERE registration_number='UPGRADE-TEST'")
        assert stored == original
        assert cipher.decrypt(stored) == "Existing encrypted patient"
        assert await upgrade.fetchval("SELECT role::text FROM users WHERE email='admin@hms.local'") == "HOSPITAL_ADMIN"
        assert await upgrade.fetchval("SELECT count(*) FROM patients WHERE hospital_id IS NULL") == 0
    finally:
        if upgrade:
            await upgrade.close()
        await owner.execute(f'DROP DATABASE "{database_name}"')
        await owner.close()

