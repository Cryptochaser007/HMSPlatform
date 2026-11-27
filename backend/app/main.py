"""FastAPI application entrypoint for ABDM-Enabled NABH HMS Platform."""

import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.abdm.availability import require_abdm_enabled
from app.abdm.callbacks import router as abdm_v3_callbacks_router
from app.abdm.callbacks import verify_gateway_callback_request
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import check_db_health
from app.core.dependencies import RequestIDMiddleware
from app.core.wasa_security import (
    SecurityHeadersMiddleware,
    install_pii_log_filter,
    mask_pii_text,
)

settings = get_settings()
install_pii_log_filter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle events: startup checks and resource teardown."""
    # Startup: Verify database connection
    health = await check_db_health()
    if health["status"] != "healthy":
        print(f"⚠️  Database connection warning during startup: {health}")
    else:
        print("✅ Database connection established successfully.")
    yield
    # Shutdown
    from app.core import dependencies, redis_state, security
    from app.core.database import engine
    for module, attribute in ((dependencies, "_redis_pool"),
                              (redis_state, "_client"), (security, "_redis_pool")):
        client = getattr(module, attribute)
        if client is not None:
            await client.aclose()
            setattr(module, attribute, None)
    await engine.dispose()
    print("🛑 Shutting down HMS Platform API server.")


is_production = settings.ENVIRONMENT.lower() == "production"
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
# Cloud-based ABDM-Enabled Hospital Management System (HMS) tailored for NABH

### Compliant with:
- **India DPDP Act (Digital Personal Data Protection Act)**: Consent management, PII encryption at rest, Right-to-Erasure.
- **DISHA Guidelines**: Field-level encryption, TLS 1.3 in transit, immutable SHA-256 hash-chain audit logs.
- **ABDM (Ayushman Bharat Digital Mission)**: ABHA ID creation, HIP/HIU workflows, HPR/HFR integration, FHIR R4 document bundles.
- **NABH Standards**: Quality indicators, clinical incident reports, medication safety audits.

### Core Modules:
1. Patient Registration & Demographics
2. OPD/IPD Workflows & Clinic Queues
3. Electronic Medical Records (EMR)
4. Pharmacy & Inventory Control
5. Laboratory Information System (LIS)
6. Radiology & PACS (OHIF Viewer)
7. Billing & Revenue Management
8. Quality & Accreditation Management
    """,
    openapi_url=None if is_production else "/api/v1/openapi.json",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Request-ID",
        "X-CM-ID",
        "REQUEST-ID",
        "TIMESTAMP",
        "X-CSRF-Token",
        "X-HIU-ID",
        "X-LINK-TOKEN",
        "X-ABDM-Signature",
    ],
)

# ── Global Exception Handlers ────────────────────────────────────────────────


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Preserve standard HTTP exceptions (401, 403, 404) with PII-masked detail."""
    detail = mask_pii_text(exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled runtime errors, log PII-masked traceback, and return WASA-safe response."""
    request_id = getattr(request.state, "request_id", "unknown")
    masked_trace = mask_pii_text(traceback.format_exc())
    print(f"[Unhandled Server Error] Request ID: {request_id}\n{masked_trace}")
    content: dict[str, Any] = {
        "detail": "An internal server error occurred. Please reference the request_id with support.",
        "request_id": request_id,
    }
    if settings.DEBUG:
        content["debug_detail"] = mask_pii_text(str(exc))
        content["error_type"] = exc.__class__.__name__
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )


# ── Health & Diagnostics ─────────────────────────────────────────────────────


@app.get("/health", tags=["System Diagnostics"])
async def health_check() -> dict[str, Any]:
    """Perform health checks on database and ABDM adapter readiness (WASA-safe)."""
    from app.abdm.config import get_abdm_settings

    abdm_cfg = get_abdm_settings()
    db_health = await check_db_health()
    db_status = db_health["database"]
    if not settings.DEBUG and db_status != "connected":
        db_status = "unavailable"
    return {
        "status": db_health["status"],
        "version": settings.VERSION,
        "database": db_status,
        "tables_initialized": db_health.get("tables_initialized", False),
        "environment": settings.ENVIRONMENT,
        "abdm_env": abdm_cfg.abdm_env.value,
    }


@app.get("/", tags=["System Diagnostics"])
async def root() -> dict[str, str]:
    """Root info endpoint."""
    payload = {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "health": "/health",
    }
    if not is_production:
        payload["docs"] = "/docs"
    return payload


# Mount API version 1
app.include_router(api_router, prefix="/api/v1")
# NHA bridge callback URLs are registered at the v3 root paths. The legacy
# /api/v1/abdm routes remain mounted above for deployed clients during migration.
app.include_router(
    abdm_v3_callbacks_router, prefix="/api",
    dependencies=[Depends(require_abdm_enabled), Depends(verify_gateway_callback_request)],
)

