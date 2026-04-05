from __future__ import annotations

from market_intel.domain.entities.candle import Candle
from market_intel.domain.entities.tick import TradeTick
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.modules.charting.candle_builder import CandleBuilder


def build_candles_from_ticks(
    symbol: str,
    timeframe: Timeframe,
    ticks: list[TradeTick],
) -> list[Candle]:
    b = CandleBuilder(symbol=symbol, timeframe=timeframe)
    b.extend(ticks)
    return b.to_candles()
