import math

import pandas as pd

from market_intel.ui.formatters.usd_compact import format_pivot_currency_cells, format_usd_compact


def test_format_usd_compact_k_m_b() -> None:
    assert format_usd_compact(500) == "$500"
    assert "K" in format_usd_compact(12_345)
    assert "M" in format_usd_compact(100_000_000)
    assert "B" in format_usd_compact(2.5e9)


def test_format_usd_compact_negative() -> None:
    assert format_usd_compact(-1e6).startswith("-")


def test_format_usd_compact_na() -> None:
    assert format_usd_compact(None) == "—"
    assert format_usd_compact(float("nan")) == "—"
    assert format_usd_compact(math.nan) == "—"


def test_format_pivot_currency_cells() -> None:
    df = pd.DataFrame([[1e6, "text"], [None, 100.0]])
    out = format_pivot_currency_cells(df)
    assert "M" in str(out.iloc[0, 0])
    assert out.iloc[0, 1] == "text"
    assert out.iloc[1, 0] == "—"
