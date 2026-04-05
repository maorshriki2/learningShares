from __future__ import annotations

from fastapi import APIRouter, Depends

from market_intel.api.dependencies import get_market_service
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.modules.charting.indicators.fibonacci import fibonacci_levels_from_swing

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/{symbol}/ohlcv")
async def ohlcv(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    limit: int = 300,
    service: MarketDataService = Depends(get_market_service),
) -> dict[str, object]:
    df = await service.historical_frame(symbol.upper(), timeframe, limit)
    candles = service.candles_to_dto(df)
    patterns = service.detect_patterns(df)
    indicators = service.indicator_bundle(df)
    fib = None
    if not df.empty and len(df) >= 20:
        hi = float(df["high"].max())
        lo = float(df["low"].min())
        fib = fibonacci_levels_from_swing(hi, lo)
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.value,
        "candles": [c.model_dump(mode="json") for c in candles],
        "patterns": [p.model_dump() for p in patterns],
        "indicators": indicators,
        "fibonacci": {
            "swing_high": fib.swing_high,
            "swing_low": fib.swing_low,
            "direction": fib.direction,
            "levels": fib.levels,
        }
        if fib
        else None,
    }
