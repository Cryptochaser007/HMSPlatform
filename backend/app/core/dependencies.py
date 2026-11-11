"""
Common FastAPI dependencies re-exported for convenience.

- Pagination
- Current user (from security)
- Database session (from database)
- Rate limiter
- Request ID middleware
"""

from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Query, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.database import get_db as get_database_session
from app.core.security import get_current_user as get_authenticated_user

settings = get_settings()

# ── Re-exports ───────────────────────────────────────────────────────────

get_db = get_database_session
get_current_user = get_authenticated_user


# ── Pagination ───────────────────────────────────────────────────────────

class PaginationParams:
    """Parsed and validated pagination parameters."""

    def __init__(self, page: int, page_size: int) -> None:
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size


async def get_pagination(
    page: int = Query(1, ge=1, le=10_000, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """FastAPI dependency for paginated list endpoints."""
    return PaginationParams(page=page, page_size=page_size)


# ── Rate limiter ─────────────────────────────────────────────────────────

_redis_pool: Optional[aioredis.Redis] = None


async def _get_rate_limit_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_pool


class RateLimiter:
    """Simple sliding-window rate limiter backed by Redis.

    Usage as a dependency::

        @router.get("/endpoint", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
        async def my_endpoint(): ...
    """

    def __init__(self, times: int = 60, seconds: int = 60) -> None:
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"rl:{client_ip}:{path}"

        try:
            r = await _get_rate_limit_redis()
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, self.seconds)
            if current > self.times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                )
        except HTTPException:
            raise
        except Exception:
            # If Redis is unavailable, allow the request through
            pass


# ── Request ID middleware ────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique ``X-Request-ID`` header to every request/response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
