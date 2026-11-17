"""FastAPI application entrypoint for ABDM-Enabled NABH HMS Platform."""

import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    print("🛑 Shutting down HMS Platform API server.")


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
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
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
    content: Dict[str, Any] = {
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
async def health_check() -> Dict[str, Any]:
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
async def root() -> Dict[str, str]:
    """Root info endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Mount API version 1
app.include_router(api_router, prefix="/api/v1")

