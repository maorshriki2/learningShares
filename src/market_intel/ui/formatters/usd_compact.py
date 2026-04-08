"""Compact USD display for Streamlit tables and metrics (SEC facts are USD)."""

from __future__ import annotations

import math

import pandas as pd


def format_usd_compact(value: float | int | None, *, na: str = "—") -> str:
    """
    Abbreviate large USD amounts: K / M / B / T with $ prefix.
    Leaves non-finite and non-numeric as `na`.
    """
    if value is None:
        return na
    try:
        v = float(value)
    except (TypeError, ValueError):
        return na
    if not math.isfinite(v):
        return na
    sign = "-" if v < 0 else ""
    av = abs(v)
    if av < 1e-9:
        return f"{sign}$0"

    def _fmt(div: float, suffix: str) -> str:
        x = av / div
        s = f"{x:.2f}".rstrip("0").rstrip(".")
        return f"{sign}${s}{suffix}"

    if av < 1_000:
        s = f"{av:.2f}".rstrip("0").rstrip(".")
        return f"{sign}${s}"
    if av < 1_000_000:
        return _fmt(1_000, "K")
    if av < 1_000_000_000:
        return _fmt(1_000_000, "M")
    if av < 1_000_000_000_000:
        return _fmt(1_000_000_000, "B")
    return _fmt(1_000_000_000_000, "T")


def format_pivot_currency_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with numeric cells replaced by format_usd_compact strings."""
    if df.empty:
        return df
    out = df.copy()

    def _cell(x: object) -> object:
        if x is None or (isinstance(x, float) and not math.isfinite(x)):
            return "—"
        if isinstance(x, (int, float)):
            return format_usd_compact(float(x))
        return x

    return out.map(_cell)
