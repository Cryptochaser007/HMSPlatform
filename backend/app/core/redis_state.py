"""Shared Redis helpers for short lived ABDM workflow state with resilient in-memory fallback."""
import json
import logging
import time
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class InMemoryRedisFallback:
    """In-memory Redis-compatible fallback when Redis server is unreachable."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}
        self._expiry: dict[str, float] = {}

    def _purge(self, key: str) -> None:
        if self._expiry.get(key, 0) and self._expiry[key] <= time.time():
            self._store.pop(key, None)
            self._expiry.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._purge(key)
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        self._purge(key)
        if nx and key in self._store:
            return False
        self._store[key] = str(value)
        if ex is not None:
            self._expiry[key] = time.time() + ex
        else:
            self._expiry.pop(key, None)
        return True

    async def delete(self, key: str) -> int:
        self._expiry.pop(key, None)
        return 1 if self._store.pop(key, None) is not None else 0

    async def incr(self, key: str) -> int:
        self._purge(key)
        current = int(self._store.get(key, 0)) + 1
        self._store[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        self._purge(key)
        if key not in self._store:
            return False
        self._expiry[key] = time.time() + seconds
        return True

    async def lpush(self, key: str, value: Any) -> int:
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].insert(0, str(value))
        return len(self._lists[key])

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        if key in self._lists:
            self._lists[key] = self._lists[key][start : end + 1]
        return True

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        lst = self._lists.get(key, [])
        if end == -1:
            return lst[start:]
        return lst[start : end + 1]

    async def ping(self) -> bool:
        return True


_client = None
_fallback = InMemoryRedisFallback()


async def get_redis():
    global _client
    if _client is not None:
        try:
            await _client.ping()
            return _client
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            _client = None

    try:
        settings = get_settings()
        url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(
            url,
            decode_responses=True,
            health_check_interval=30,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        await client.ping()
        _client = client
        return _client
    except Exception as exc:
        logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
        logger.debug("Redis unreachable, using in-memory store: %s", exc)
        return _fallback


async def put_json(key: str, value: Any, ttl: int) -> None:
    client = await get_redis()
    await client.set(key, json.dumps(value, separators=(",", ":")), ex=ttl)


async def get_json(key: str) -> Any | None:
    client = await get_redis()
    value = await client.get(key)
    return json.loads(value) if value else None


async def acquire_idempotency(request_id: str, ttl: int = 86400) -> bool:
    if not request_id:
        return False
    client = await get_redis()
    return bool(await client.set(f"abdm:idem:{request_id}", "processing", nx=True, ex=ttl))


async def finish_idempotency(request_id: str, status: str = "done", ttl: int = 86400) -> None:
    if request_id:
        client = await get_redis()
        await client.set(f"abdm:idem:{request_id}", status, ex=ttl)
