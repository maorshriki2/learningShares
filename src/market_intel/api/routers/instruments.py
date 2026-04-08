from __future__ import annotations

import asyncio
from typing import Any

import yfinance as yf
from fastapi import APIRouter, Depends

from market_intel.api.dependencies import get_market_service
from market_intel.application.dto.instrument_dto import InstrumentSummaryDTO
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.infrastructure.market_data.instrument_info import SECTOR_MAP

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/{symbol}/summary")
async def instrument_summary(
    symbol: str,
    service: MarketDataService = Depends(get_market_service),
) -> dict[str, Any]:
    sym = (symbol or "").strip().upper()

    def _sync_info() -> dict[str, Any]:
        t = yf.Ticker(sym)
        info = t.info or {}
        return info

    info: dict[str, Any] = {}
    try:
        info = await asyncio.to_thread(_sync_info)
    except Exception:
        # Provider can intermittently fail for some symbols; keep the endpoint resilient.
        info = {}
    name = info.get("longName") or info.get("shortName")
    sector_raw = info.get("sector") or info.get("industry")
    sector = None
    if sector_raw is not None:
        sector = SECTOR_MAP.get(str(sector_raw), None)
        sector = str(sector) if sector is not None else str(sector_raw)

    market_cap = info.get("marketCap")
    beta = info.get("beta")
    price = (
        info.get("regularMarketPrice")
        or info.get("currentPrice")
        or info.get("previousClose")
    )

    vol_1y = None
    try:
        df = await service.historical_frame(sym, Timeframe.D1, limit=260)
        vol_1y = (
            service.annualized_volatility_from_close(df["close"]) if "close" in df else None
        )
    except Exception:
        vol_1y = None

    dto = InstrumentSummaryDTO(
        symbol=sym,
        name=str(name) if name is not None else None,
        sector=sector,
        market_cap=float(market_cap) if market_cap is not None else None,
        price=float(price) if price is not None else None,
        beta=float(beta) if beta is not None else None,
        volatility_1y=float(vol_1y) if vol_1y is not None else None,
    )
    return dto.model_dump(mode="json")

