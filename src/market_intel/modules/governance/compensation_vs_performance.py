from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompPerformanceView:
    symbol: str
    executive: str
    total_comp_usd: float | None
    revenue_cagr_3y: float | None
    net_income_margin_latest: float | None
    narrative: str


def explain_comp_vs_performance(
    symbol: str,
    executive: str,
    total_comp_usd: float | None,
    revenue_cagr_3y: float | None,
    net_income_margin_latest: float | None,
) -> CompPerformanceView:
    parts: list[str] = []
    if revenue_cagr_3y is not None:
        parts.append(f"3-year revenue CAGR ~ {revenue_cagr_3y * 100:.1f}%")
    if net_income_margin_latest is not None:
        parts.append(f"latest net margin ~ {net_income_margin_latest * 100:.1f}%")
    if total_comp_usd is not None:
        parts.append(f"disclosed total comp ~ ${total_comp_usd:,.0f}")
    narrative = (
        "Compare pay magnitude and structure (cash vs equity) to durable operating performance, "
        "not single-year stock moves. Rising equity-heavy pay with weak ROIC may signal "
        "misalignment; modest pay with strong reinvestment economics may be favorable."
    )
    return CompPerformanceView(
        symbol=symbol,
        executive=executive,
        total_comp_usd=total_comp_usd,
        revenue_cagr_3y=revenue_cagr_3y,
        net_income_margin_latest=net_income_margin_latest,
        narrative=narrative,
    )
