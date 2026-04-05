from __future__ import annotations

import pandas as pd


def session_vwap(df: pd.DataFrame, typical_price_col: str | None = None) -> pd.Series:
    """
    Volume-weighted average price using typical price (H+L+C)/3 per row.
    Expects columns: high, low, close, volume (or user-specified typical column).
    """
    if df.empty:
        return pd.Series(dtype=float)
    if typical_price_col:
        tp = df[typical_price_col].astype(float)
    else:
        tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float).clip(lower=0.0)
    cum_pv = (tp * vol).cumsum()
    cum_v = vol.cumsum().replace(0.0, pd.NA)
    vwap = cum_pv / cum_v
    return vwap.astype(float)
