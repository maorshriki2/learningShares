from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class AsyncRateLimiter:
    def __init__(self, max_calls: int, period_seconds: float) -> None:
        self._max_calls = max_calls
        self._period = period_seconds
        self._lock = asyncio.Lock()
        self._window_start = time.monotonic()
        self._calls = 0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now - self._window_start >= self._period:
                self._window_start = now
                self._calls = 0
            if self._calls >= self._max_calls:
                sleep_for = self._period - (now - self._window_start)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                self._window_start = time.monotonic()
                self._calls = 0
            self._calls += 1

    async def run(self, fn: Callable[[], Awaitable[T]]) -> T:
        await self.acquire()
        return await fn()
