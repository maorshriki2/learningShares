from __future__ import annotations

from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe


async def compute_indicators_for_symbol(
    service: MarketDataService,
    symbol: str,
    limit: int = 300,
) -> dict[str, object]:
    df = await service.historical_frame(symbol, Timeframe.D1, limit)
    return service.indicator_bundle(df)
