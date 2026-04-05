import pandas as pd

from market_intel.modules.charting.indicators.macd import macd
from market_intel.modules.charting.indicators.rsi import rsi
from market_intel.modules.charting.indicators.vwap import session_vwap


def test_rsi_bounds() -> None:
    close = pd.Series(range(1, 50), dtype=float)
    out = rsi(close, 14)
    assert len(out) == len(close)
    assert out.iloc[-1] <= 100


def test_macd_shapes() -> None:
    close = pd.Series([float(i % 10 + 1) for i in range(60)])
    out = macd(close)
    assert "macd" in out.columns
    assert len(out) == len(close)


def test_vwap_monotonic_volume() -> None:
    df = pd.DataFrame(
        {
            "high": [10, 11, 12],
            "low": [9, 10, 11],
            "close": [9.5, 10.5, 11.5],
            "volume": [100, 100, 100],
        }
    )
    v = session_vwap(df)
    assert len(v) == 3
