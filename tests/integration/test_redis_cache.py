import os

import pytest


@pytest.mark.asyncio
async def test_redis_ping_optional() -> None:
    url = os.environ.get("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not set")
    redis = pytest.importorskip("redis.asyncio")
    client = redis.from_url(url, encoding="utf-8", decode_responses=True)
    try:
        pong = await client.ping()
        assert pong is True
    finally:
        await client.aclose()
