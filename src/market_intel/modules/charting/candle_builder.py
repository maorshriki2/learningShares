from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

import pandas as pd

from market_intel.domain.entities.candle import Candle
from market_intel.domain.entities.tick import TradeTick
from market_intel.domain.value_objects.timeframe import Timeframe


def _floor_bucket(ts: datetime, delta: timedelta) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    seconds = (ts - epoch).total_seconds()
    step = delta.total_seconds()
    bucket = int(seconds // step) * step
    return epoch + timedelta(seconds=bucket)


_TIMEFRAME_DELTA: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(days=7),
    Timeframe.MO1: timedelta(days=30),
}


def ticks_to_ohlcv_df(ticks: list[TradeTick], timeframe: Timeframe) -> pd.DataFrame:
    if not ticks:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    delta = _TIMEFRAME_DELTA[timeframe]
    rows: list[dict[str, object]] = []
    current_bucket: datetime | None = None
    o = h = l = c = 0.0
    v = 0.0
    for t in sorted(ticks, key=lambda x: x.ts):
        b = _floor_bucket(t.ts, delta)
        if current_bucket is None:
            current_bucket = b
            o = h = l = c = float(t.price)
            v = float(t.size)
            continue
        if b != current_bucket:
            rows.append(
                {
                    "ts": current_bucket,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": v,
                }
            )
            current_bucket = b
            o = h = l = c = float(t.price)
            v = float(t.size)
        else:
            px = float(t.price)
            h = max(h, px)
            l = min(l, px)
            c = px
            v += float(t.size)
    if current_bucket is not None:
        rows.append(
            {
                "ts": current_bucket,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df.set_index("ts", inplace=True)
    return df


@dataclass
class CandleBuilder:
    symbol: str
    timeframe: Timeframe
    max_ticks: int = 5000
    _ticks: deque[TradeTick] = field(default_factory=deque)

    def push(self, tick: TradeTick) -> None:
        self._ticks.append(tick)
        while len(self._ticks) > self.max_ticks:
            self._ticks.popleft()

    def extend(self, ticks: Iterable[TradeTick]) -> None:
        for t in ticks:
            self.push(t)

    def to_candles(self) -> list[Candle]:
        delta = _TIMEFRAME_DELTA[self.timeframe]
        ticks_list = list(self._ticks)
        if not ticks_list:
            return []
        buckets: dict[datetime, dict[str, float]] = {}
        order: list[datetime] = []
        for t in sorted(ticks_list, key=lambda x: x.ts):
            b = _floor_bucket(t.ts, delta)
            px = float(t.price)
            sz = float(t.size)
            if b not in buckets:
                buckets[b] = {"o": px, "h": px, "l": px, "c": px, "v": sz}
                order.append(b)
            else:
                cur = buckets[b]
                cur["h"] = max(cur["h"], px)
                cur["l"] = min(cur["l"], px)
                cur["c"] = px
                cur["v"] += sz
        candles: list[Candle] = []
        for b in order:
            cur = buckets[b]
            candles.append(
                Candle(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    ts=b,
                    open=cur["o"],
                    high=cur["h"],
                    low=cur["l"],
                    close=cur["c"],
                    volume=cur["v"],
                )
            )
        return candles

    def to_dataframe(self) -> pd.DataFrame:
        candles = self.to_candles()
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        data = {
            "ts": [c.ts for c in candles],
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
        df = pd.DataFrame(data)
        df.set_index("ts", inplace=True)
        return df
