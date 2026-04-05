from __future__ import annotations

from collections.abc import AsyncIterator

from market_intel.config.settings import Settings
from market_intel.domain.entities.tick import TradeTick
from market_intel.infrastructure.market_data.provider_chain import stream_trade_ticks


async def stream_ticks_for_symbol(settings: Settings, symbol: str) -> AsyncIterator[TradeTick]:
    async for tick in stream_trade_ticks(settings, symbol):
        yield tick
