from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import redis.asyncio as redis

from market_intel.config.settings import Settings


class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            val, exp = item
            if exp is not None and time.time() > exp:
                del self._data[key]
                return None
            return val

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        async with self._lock:
            exp = time.time() + ttl_seconds if ttl_seconds else None
            self._data[key] = (value, exp)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)


class RedisCache:
    def __init__(self, client: redis.Redis) -> None:
        self._r = client

    async def get(self, key: str) -> str | None:
        v = await self._r.get(key)
        if v is None:
            return None
        if isinstance(v, bytes):
            return v.decode("utf-8")
        return str(v)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds:
            await self._r.set(key, value, ex=ttl_seconds)
        else:
            await self._r.set(key, value)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)


async def create_cache(settings: Settings) -> MemoryCache | RedisCache:
    if not settings.redis_url:
        return MemoryCache()
    client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await client.ping()
    return RedisCache(client)


def cache_key(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}:{json.dumps(payload, sort_keys=True, default=str)}"
