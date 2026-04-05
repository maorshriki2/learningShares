from __future__ import annotations

import httpx

from market_intel.config.settings import Settings


def create_async_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout_seconds),
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        headers={"User-Agent": settings.sec_user_agent},
        follow_redirects=True,
    )
