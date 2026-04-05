from __future__ import annotations

import pandas as pd


def _donchian_mid(high: pd.Series, low: pd.Series, length: int) -> pd.Series:
    hh = high.rolling(window=length, min_periods=1).max()
    ll = low.rolling(window=length, min_periods=1).min()
    return (hh + ll) / 2.0


def ichimoku_cloud(
    df: pd.DataFrame,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52,
) -> pd.DataFrame:
    """
    Ichimoku Kinko Hyo components on OHLCV DataFrame (index: time).
    Senkou spans are shifted forward by kijun periods (standard convention).
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "tenkan",
                "kijun",
                "senkou_a",
                "senkou_b",
                "chikou",
            ]
        )
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    tenkan_sen = _donchian_mid(high, low, tenkan)
    kijun_sen = _donchian_mid(high, low, kijun)
    senkou_a = (tenkan_sen + kijun_sen) / 2.0
    senkou_a_lead = senkou_a.shift(kijun)
    senkou_b_line = _donchian_mid(high, low, senkou_b)
    senkou_b_lead = senkou_b_line.shift(kijun)
    chikou = close.shift(-kijun)

    out = pd.DataFrame(
        {
            "tenkan": tenkan_sen,
            "kijun": kijun_sen,
            "senkou_a": senkou_a_lead,
            "senkou_b": senkou_b_lead,
            "chikou": chikou,
        },
        index=df.index,
    )
    return out
