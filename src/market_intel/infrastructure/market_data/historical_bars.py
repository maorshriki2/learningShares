from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from market_intel.domain.entities.candle import Candle
from market_intel.domain.value_objects.timeframe import Timeframe


_INTERVAL_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.H1: "60m",
    Timeframe.D1: "1d",
    Timeframe.W1: "1wk",
    Timeframe.MO1: "1mo",
}


class YFinanceHistoricalAdapter:
    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> list[Candle]:
        interval = _INTERVAL_MAP[timeframe]
        ticker = yf.Ticker(symbol)

        def _choose_period(interval0: str, limit0: int) -> str:
            """
            yfinance's `history()` behaves differently depending on which params are passed.
            When `start`/`end` are None, use an explicit `period` so we don't accidentally get
            a very short default window (often ~1 month), which breaks feature engineering.
            """
            if interval0 in ("1m", "5m", "15m", "60m"):
                # Intraday periods are restricted anyway; leave to caller.
                return "1mo"
            # Approx trading bars per year for daily, otherwise smaller.
            bars_per_year = 252 if interval0 == "1d" else 52 if interval0 == "1wk" else 12
            years = max(1, int((max(1, int(limit0)) / bars_per_year) + 1))
            if years <= 1:
                return "1y"
            if years <= 2:
                return "2y"
            if years <= 5:
                return "5y"
            if years <= 10:
                return "10y"
            return "max"

        def _load() -> pd.DataFrame:
            if start is None:
                # Use `period` to avoid yfinance defaulting to a short window.
                return ticker.history(
                    period=_choose_period(interval, limit),
                    interval=interval,
                    auto_adjust=False,
                )
            return ticker.history(start=start, end=end, interval=interval, auto_adjust=False)

        df = await asyncio.to_thread(_load)
        if df.empty:
            return []
        df = df.tail(limit)
        candles: list[Candle] = []
        for ts, row in df.iterrows():
            if hasattr(ts, "to_pydatetime"):
                tsd = ts.to_pydatetime()
            else:
                tsd = datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc)
            if tsd.tzinfo is None:
                tsd = tsd.replace(tzinfo=timezone.utc)
            o = float(row["Open"])
            h = float(row["High"])
            l = float(row["Low"])
            c = float(row["Close"])
            v = float(row.get("Volume", 0) or 0)
            if o <= 0 or h <= 0 or l <= 0 or c <= 0:
                continue
            candles.append(
                Candle(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    ts=tsd,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v,
                )
            )
        return candles


async def yfinance_history_dataframe(
    symbol: str, period: str = "1y", interval: str = "1d"
) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)

    def _load() -> pd.DataFrame:
        return ticker.history(period=period, interval=interval, auto_adjust=False)

    return await asyncio.to_thread(_load)
