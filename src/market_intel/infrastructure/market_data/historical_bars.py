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

        def _load() -> pd.DataFrame:
            return ticker.history(
                start=start,
                end=end,
                interval=interval,
                auto_adjust=False,
            )

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
