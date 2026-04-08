from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, Request

from market_intel.application.services.fundamentals_service import FundamentalsService
from market_intel.application.services.governance_service import GovernanceService
from market_intel.application.services.market_context_service import MarketContextService
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.application.services.portfolio_service import PortfolioService
from market_intel.config.settings import Settings, get_settings
from market_intel.infrastructure.cache.redis_cache import MemoryCache, RedisCache, create_cache
from market_intel.infrastructure.fundamentals.sec_company_facts_adapter import (
    SecCompanyFactsFundamentalsAdapter,
)
from market_intel.infrastructure.http.client import create_async_client
from market_intel.infrastructure.http.rate_limit import AsyncRateLimiter
from market_intel.infrastructure.market_data.historical_bars import YFinanceHistoricalAdapter
from market_intel.infrastructure.market_context.providers import (
    FmpProvider,
    NewsApiProvider,
    YFinanceNewsProvider,
)
from market_intel.infrastructure.market_context.social_scrapers import Tier3SocialSentimentProvider
from market_intel.infrastructure.nlp.finbert_engine import FinBertSentimentAdapter
from market_intel.infrastructure.persistence.json_portfolio_repo import JsonPortfolioRepository
from market_intel.infrastructure.sec.sec_edgar_adapter import SecEdgarHttpAdapter
from market_intel.infrastructure.transcripts.provider import FinnhubTranscriptAdapter


@dataclass
class AppState:
    settings: Settings
    http_client: httpx.AsyncClient
    cache: MemoryCache | RedisCache
    rate_limiter: AsyncRateLimiter
    sec: SecEdgarHttpAdapter
    fundamentals_adapter: SecCompanyFactsFundamentalsAdapter
    finbert: FinBertSentimentAdapter
    transcripts: FinnhubTranscriptAdapter
    historical: YFinanceHistoricalAdapter
    fundamentals_service: FundamentalsService
    governance_service: GovernanceService
    market_service: MarketDataService
    market_context_service: MarketContextService
    portfolio_service: PortfolioService


async def build_app_state(settings: Settings) -> AppState:
    client = create_async_client(settings)
    try:
        cache = await create_cache(settings)
    except Exception:
        cache = MemoryCache()
    rate = AsyncRateLimiter(max_calls=9, period_seconds=1.0)
    sec = SecEdgarHttpAdapter(settings, client, cache, rate)
    fundamentals_adapter = SecCompanyFactsFundamentalsAdapter(
        settings, client, cache, rate, sec
    )
    finbert = FinBertSentimentAdapter(settings)
    transcripts = FinnhubTranscriptAdapter(settings, client, cache)
    historical = YFinanceHistoricalAdapter()
    fundamentals_service = FundamentalsService(fundamentals_adapter)
    governance_service = GovernanceService(sec, transcripts, finbert, settings, client)
    market_service = MarketDataService(historical)
    fmp = FmpProvider(settings, client, cache)
    newsapi = NewsApiProvider(settings, client, cache)
    yfinance_news = YFinanceNewsProvider()
    social = Tier3SocialSentimentProvider(
        settings=settings,
        client=client,
        cache=cache,
        nitter_instances=(settings.nitter_instances_list or None),
    )
    market_context_service = MarketContextService(
        sec=sec,
        finbert=finbert,
        settings=settings,
        http_client=client,
        fmp=fmp,
        newsapi=newsapi,
        social=social,
        yfinance_news=yfinance_news,
    )
    portfolio_repo = JsonPortfolioRepository(settings)
    portfolio_service = PortfolioService(portfolio_repo)
    return AppState(
        settings=settings,
        http_client=client,
        cache=cache,
        rate_limiter=rate,
        sec=sec,
        fundamentals_adapter=fundamentals_adapter,
        finbert=finbert,
        transcripts=transcripts,
        historical=historical,
        fundamentals_service=fundamentals_service,
        governance_service=governance_service,
        market_service=market_service,
        market_context_service=market_context_service,
        portfolio_service=portfolio_service,
    )


def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state


StateDep = Annotated[AppState, Depends(get_app_state)]


def get_fundamentals_service(state: StateDep) -> FundamentalsService:
    return state.fundamentals_service


def get_governance_service(state: StateDep) -> GovernanceService:
    return state.governance_service


def get_market_service(state: StateDep) -> MarketDataService:
    return state.market_service


def get_market_context_service(state: StateDep) -> MarketContextService:
    return state.market_context_service


def get_portfolio_service(state: StateDep) -> PortfolioService:
    return state.portfolio_service


def get_settings_dep() -> Settings:
    return get_settings()
