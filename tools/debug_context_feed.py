from __future__ import annotations

import asyncio
import sys
import traceback

import httpx

from market_intel.application.services.market_context_service import MarketContextService
from market_intel.config.settings import Settings
from market_intel.infrastructure.cache.redis_cache import MemoryCache
from market_intel.infrastructure.http.rate_limit import AsyncRateLimiter
from market_intel.infrastructure.market_context.providers import (
    FmpProvider,
    NewsApiProvider,
    YFinanceNewsProvider,
)
from market_intel.infrastructure.market_context.social_scrapers import Tier3SocialSentimentProvider
from market_intel.infrastructure.nlp.finbert_engine import FinBertSentimentAdapter
from market_intel.infrastructure.sec.sec_edgar_adapter import SecEdgarHttpAdapter


async def main() -> int:
    sym = (sys.argv[1] if len(sys.argv) > 1 else "AAOI").strip().upper()
    settings = Settings()
    cache = MemoryCache()
    rate = AsyncRateLimiter(max_calls=9, period_seconds=1.0)

    async with httpx.AsyncClient() as client:
        sec = SecEdgarHttpAdapter(settings, client, cache, rate)
        fin = FinBertSentimentAdapter(settings)
        fmp = FmpProvider(settings, client, cache)
        news = NewsApiProvider(settings, client, cache)
        yfn = YFinanceNewsProvider()
        social = Tier3SocialSentimentProvider(
            settings=settings,
            client=client,
            cache=cache,
            nitter_instances=(settings.nitter_instances_list or None),
        )
        svc = MarketContextService(
            sec=sec,
            finbert=fin,
            settings=settings,
            http_client=client,
            fmp=fmp,
            newsapi=news,
            social=social,
            yfinance_news=yfn,
        )

        try:
            dto = await svc.build_feed(sym)
        except Exception:
            print("\n=== build_feed EXCEPTION ===\n")
            print(traceback.format_exc())
            return 1

        print("\n=== build_feed OK ===\n")
        print(f"symbol={dto.symbol} ok={dto.ok} as_of={dto.as_of}")
        for s in dto.sections:
            n = len(s.items or [])
            print(f"- {s.id}: items={n} ai_debug={s.ai_debug}")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

