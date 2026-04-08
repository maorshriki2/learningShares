from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from market_intel.application.dto.market_dto import CandleDTO, PatternDTO, TickDTO
from market_intel.domain.entities.tick import TradeTick
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.infrastructure.market_data.historical_bars import YFinanceHistoricalAdapter
from market_intel.modules.charting.indicators.ichimoku import ichimoku_cloud
from market_intel.modules.charting.indicators.macd import macd
from market_intel.modules.charting.indicators.rsi import rsi
from market_intel.modules.charting.indicators.vwap import session_vwap
from market_intel.modules.charting.patterns.bull_flag import detect_bull_flag
from market_intel.modules.charting.patterns.head_shoulders import detect_head_and_shoulders


class MarketDataService:
    def __init__(self, historical: YFinanceHistoricalAdapter) -> None:
        self._historical = historical

    @staticmethod
    def annualized_volatility_from_close(
        close: pd.Series, periods_per_year: int = 252
    ) -> float | None:
        if close is None or close.empty:
            return None
        rets = close.astype(float).pct_change().dropna()
        if rets.empty:
            return None
        vol = float(rets.std(ddof=0)) * (periods_per_year**0.5)
        if vol != vol:  # NaN
            return None
        return vol

    async def historical_frame(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 300,
    ) -> pd.DataFrame:
        end = datetime.now(timezone.utc)
        start = None
        candles = await self._historical.get_historical_candles(
            symbol, timeframe, start, end, limit
        )
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

    def detect_patterns(self, df: pd.DataFrame) -> list[PatternDTO]:
        out: list[PatternDTO] = []
        for p in detect_head_and_shoulders(df):
            meta = dict(p.meta)
            meta.setdefault(
                "thresholds",
                {
                    "order": 3,
                    "symmetry_tolerance": 0.04,
                    "neckline_break_frac": 0.002,
                },
            )
            out.append(
                PatternDTO(
                    name=p.name,
                    start_index=p.start_index,
                    end_index=p.end_index,
                    confidence=p.confidence,
                    meta=meta,
                )
            )
        for p in detect_bull_flag(df):
            meta = dict(p.meta)
            meta.setdefault(
                "thresholds",
                {
                    "pole_lookback": 12,
                    "flag_lookback": 10,
                    "min_pole_return": 0.03,
                    "max_flag_depth": 0.02,
                },
            )
            out.append(
                PatternDTO(
                    name=p.name,
                    start_index=p.start_index,
                    end_index=p.end_index,
                    confidence=p.confidence,
                    meta=meta,
                )
            )
        return out

    def indicator_bundle(self, df: pd.DataFrame) -> dict[str, list[float | None]]:
        if df.empty:
            return {"vwap": [], "rsi14": [], "macd": [], "macd_signal": [], "ichimoku_tenkan": []}
        vwap = session_vwap(df).tolist()
        r = rsi(df["close"], 14).tolist()
        m = macd(df["close"])
        ichi = ichimoku_cloud(df)
        return {
            "vwap": [float(x) if x == x else None for x in vwap],
            "rsi14": [float(x) if x == x else None for x in r],
            "macd": [float(x) if x == x else None for x in m["macd"].tolist()],
            "macd_signal": [float(x) if x == x else None for x in m["signal"].tolist()],
            "macd_histogram": [float(x) if x == x else None for x in m["histogram"].tolist()],
            "ichimoku_tenkan": [float(x) if x == x else None for x in ichi["tenkan"].tolist()],
            "ichimoku_kijun": [float(x) if x == x else None for x in ichi["kijun"].tolist()],
            "ichimoku_senkou_a": [float(x) if x == x else None for x in ichi["senkou_a"].tolist()],
            "ichimoku_senkou_b": [float(x) if x == x else None for x in ichi["senkou_b"].tolist()],
        }

    def candles_to_dto(self, df: pd.DataFrame) -> list[CandleDTO]:
        out: list[CandleDTO] = []
        for ts, row in df.iterrows():
            tsd = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
            out.append(
                CandleDTO(
                    ts=tsd,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0) or 0),
                )
            )
        return out

    def tick_to_dto(self, tick: TradeTick) -> TickDTO:
        return TickDTO(
            symbol=tick.symbol,
            ts=tick.ts,
            price=tick.price,
            size=tick.size,
            source=tick.source,
        )
