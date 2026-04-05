from __future__ import annotations

from market_intel.application.dto.market_dto import PatternDTO
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe


async def detect_patterns_for_symbol(
    service: MarketDataService,
    symbol: str,
    limit: int = 300,
) -> list[PatternDTO]:
    df = await service.historical_frame(symbol, Timeframe.D1, limit)
    return service.detect_patterns(df)
