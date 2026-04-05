from __future__ import annotations

from typing import Iterable


def roic_series(
    nopat_by_year: dict[int, float],
    invested_capital_by_year: dict[int, float],
) -> dict[int, float]:
    """
    ROIC = NOPAT / Invested Capital (simple point-in-time capital base).
    """
    out: dict[int, float] = {}
    years: Iterable[int] = sorted(set(nopat_by_year) & set(invested_capital_by_year))
    for y in years:
        ic = invested_capital_by_year[y]
        if ic == 0:
            continue
        out[y] = nopat_by_year[y] / ic
    return out


def nopat_from_operating_income(
    operating_income: float,
    tax_rate: float,
) -> float:
    return operating_income * (1.0 - tax_rate)
