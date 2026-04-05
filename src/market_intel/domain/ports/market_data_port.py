from datetime import datetime
from typing import AsyncIterator, Protocol

from market_intel.domain.entities.candle import Candle
from market_intel.domain.value_objects.timeframe import Timeframe


class MarketDataPort(Protocol):
    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> list[Candle]: ...
