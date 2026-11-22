"""
Common FastAPI dependencies re-exported for convenience.

- Pagination
- Current user (from security)
- Database session (from database)
- Rate limiter
- Request ID middleware
"""

import logging
import os
import time
from collections import defaultdict, deque
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import HTTPException, Query, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

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

_redis_pool: aioredis.Redis | None = None


async def _get_rate_limit_redis() -> aioredis.Redis | None:
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.ping()
            return _redis_pool
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            _redis_pool = None

    redis_url = getattr(settings, "REDIS_URL", "")
    if not redis_url or (os.environ.get("VERCEL") and "localhost" in redis_url):
        return None

    try:
        client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        await client.ping()
        _redis_pool = client
        return _redis_pool
    except Exception:
        logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
        return None


_memory_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


class RateLimiter:
    """Sliding-window rate limiter backed by Redis with an automatic in-memory fallback.

    Ensures CERT-In WASA brute-force and OTP-flooding protection remains enforced even
    in serverless deployments where Redis is unavailable.
    """

    def __init__(self, times: int = 60, seconds: int = 60) -> None:
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        # The ASGI server resolves trusted proxy headers. Raw client-supplied
        # X-Forwarded-For must not let callers reset their rate-limit bucket.
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"rl:{client_ip}:{path}"

        try:
            r = await _get_rate_limit_redis()
            if r is not None:
                current = await r.incr(key)
                if current == 1:
                    await r.expire(key, self.seconds)
                if current > self.times:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later.",
                        headers={"Retry-After": str(self.seconds)},
                    )
                return
        except HTTPException:
            raise
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            # Fail-closed with per-process sliding-window fallback
            now = time.monotonic()
            cutoff = now - self.seconds
            bucket = _memory_rate_buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(self.seconds)},
                )
            bucket.append(now)


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
