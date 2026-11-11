"""FastAPI application entrypoint for ABDM-Enabled NABH HMS Platform."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import check_db_health
from app.core.dependencies import RequestIDMiddleware

settings = get_settings()


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

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers ────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected internal server error occurred.",
            "request_id": request_id,
        },
    )


# ── Health & Diagnostics ─────────────────────────────────────────────────────


@app.get("/health", tags=["System Diagnostics"])
async def health_check() -> Dict[str, str]:
    """Perform health checks on database and core services."""
    db_health = await check_db_health()
    return {
        "status": db_health["status"],
        "version": settings.VERSION,
        "database": db_health["database"],
        "database_host": db_health.get("database_host", "unknown"),
        "environment": settings.ENVIRONMENT,
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

