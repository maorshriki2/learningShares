from __future__ import annotations

import asyncio
import math
import random
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import yfinance as yf

from market_intel.config.settings import Settings
from market_intel.domain.entities.tick import TradeTick
from market_intel.infrastructure.market_data.finnhub_ws import stream_finnhub_trades
from market_intel.infrastructure.market_data.polygon_ws import stream_polygon_trades


async def _yfinance_poll_trades(symbol: str, interval_sec: float = 2.0) -> AsyncIterator[TradeTick]:
    sym = symbol.upper()
    ticker = yf.Ticker(sym)
    last_price: float | None = None
    while True:
        try:
            fast = ticker.fast_info
            px = fast.get("last_price") or fast.get("regular_market_price")
            if px is None:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    px = float(hist["Close"].iloc[-1])
            if px is not None and (last_price is None or abs(px - last_price) > 1e-6):
                last_price = float(px)
                now = datetime.now(timezone.utc)
                jitter = random.uniform(0.5, 2.0)
                yield TradeTick(
                    symbol=sym,
                    ts=now,
                    price=last_price,
                    size=jitter * 10,
                    source="yfinance",
                )
        except Exception:
            now = datetime.now(timezone.utc)
            base = last_price or 100.0
            wiggle = base * (1.0 + 0.001 * math.sin(now.timestamp() / 5.0))
            last_price = wiggle
            yield TradeTick(
                symbol=sym,
                ts=now,
                price=float(wiggle),
                size=1.0,
                source="synthetic",
            )
        await asyncio.sleep(interval_sec)


async def stream_trade_ticks(settings: Settings, symbol: str) -> AsyncIterator[TradeTick]:
    if settings.polygon_api_key:
        try:
            async for t in stream_polygon_trades(settings.polygon_api_key, symbol):
                yield t
            return
        except Exception:
            pass
    if settings.finnhub_api_key:
        try:
            async for t in stream_finnhub_trades(settings.finnhub_api_key, symbol):
                yield t
            return
        except Exception:
            pass
    async for t in _yfinance_poll_trades(symbol):
        yield t
