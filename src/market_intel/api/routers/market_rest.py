from __future__ import annotations

import logging
import traceback
from fastapi import APIRouter, Depends

from market_intel.api.dependencies import get_market_context_service, get_market_service
from market_intel.application.services.market_context_service import MarketContextService
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.modules.charting.indicators.fibonacci import fibonacci_levels_from_swing
from market_intel.modules.analytics.chart_technical_verdict import build_chart_technical_snapshot

router = APIRouter(prefix="/market", tags=["market"])
_LOG = logging.getLogger(__name__)


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


@router.get("/{symbol}/context-feed")
async def market_context_feed(
    symbol: str,
    svc: MarketContextService = Depends(get_market_context_service),
) -> dict[str, object]:
    """
    External intelligence feed (Layer 1 ingestion + Layer 2 NLP processing).
    Must be fail-soft: provider errors should never crash the dashboard.
    """
    try:
        dto = await svc.build_feed(symbol.upper())
        return dto.model_dump(mode="json")
    except Exception as exc:
        # Absolute last-resort safety: keep UI rendering even if something unexpected breaks.
        _LOG.exception("market_context_feed failed for symbol=%s: %s", symbol, exc)
        tb = traceback.format_exc()
        sym = symbol.upper()
        return {
            "ok": True,
            "symbol": sym,
            "as_of": None,
            "message_he": "התרחשה תקלה זמנית בשכבת ההקשר — מוצג feed ריק כדי לשמור יציבות.",
            "error": f"{type(exc).__name__}: {exc}",
            "error_trace": tb[-4000:],
            "sections": [
                {"id": "news", "title_he": "חדשות ודיווחים", "subtitle_he": "", "items": []},
                {"id": "macro_speeches", "title_he": "מקרו", "subtitle_he": "", "items": []},
                {"id": "rumors", "title_he": "שמועות", "subtitle_he": "", "items": []},
                {"id": "corporate", "title_he": "אירועי חברה", "subtitle_he": "", "items": []},
            ],
        }


@router.get("/{symbol}/chart-technical-verdict")
async def chart_technical_verdict(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    limit: int = 320,
    service: MarketDataService = Depends(get_market_service),
) -> dict[str, object]:
    """
    Chart-only verdict computed server-side from the same OHLCV payload as Charting Lab.
    Used by Stock360 composition and by the unified analysis artifact.
    """
    df = await service.historical_frame(symbol.upper(), timeframe, limit)
    candles = service.candles_to_dto(df)
    patterns = service.detect_patterns(df)
    indicators = service.indicator_bundle(df)
    fib = None
    if not df.empty and len(df) >= 20:
        hi = float(df["high"].max())
        lo = float(df["low"].min())
        fib = fibonacci_levels_from_swing(hi, lo)
    fib_payload = (
        {
            "swing_high": fib.swing_high,
            "swing_low": fib.swing_low,
            "direction": fib.direction,
            "levels": fib.levels,
        }
        if fib
        else None
    )

    snapshot = build_chart_technical_snapshot(
        candles=[c.model_dump(mode="json") for c in candles],
        indicators=indicators,
        patterns=[p.model_dump() for p in patterns],
        fibonacci=fib_payload,
    )
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe.value,
        "limit": int(limit),
        "snapshot": snapshot,
    }
