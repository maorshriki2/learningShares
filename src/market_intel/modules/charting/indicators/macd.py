from __future__ import annotations

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=1).mean()


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    c = close.astype(float)
    ema_fast = _ema(c, fast)
    ema_slow = _ema(c, slow)
    line = ema_fast - ema_slow
    sig = _ema(line, signal)
    hist = line - sig
    return pd.DataFrame({"macd": line, "signal": sig, "histogram": hist}, index=c.index)
