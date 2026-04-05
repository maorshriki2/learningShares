from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DcfInputs:
    base_free_cash_flow: float
    growth_years_1_to_5: float
    terminal_growth: float
    wacc: float
    projection_years: int = 5


@dataclass(frozen=True)
class DcfResult:
    enterprise_value: float
    pv_explicit: float
    pv_terminal: float
    terminal_value: float
    implied_per_share: float | None
    shares_outstanding: float | None


def discounted_cash_flow_value(
    inputs: DcfInputs,
    shares_outstanding: float | None = None,
    net_debt: float = 0.0,
) -> DcfResult:
    """
    Two-stage DCF: constant growth for projection_years, then Gordon terminal value.
    EV = PV(FCFs) + PV(TV); equity value = EV - net_debt
    """
    wacc = max(inputs.wacc, 0.0005)
    g1 = inputs.growth_years_1_to_5
    gt = min(inputs.terminal_growth, wacc - 0.0005)
    fcf = inputs.base_free_cash_flow
    pv = 0.0
    for t in range(1, inputs.projection_years + 1):
        fcf *= 1.0 + g1
        pv += fcf / ((1.0 + wacc) ** t)
    tv = fcf * (1.0 + gt) / (wacc - gt)
    pv_tv = tv / ((1.0 + wacc) ** inputs.projection_years)
    ev = pv + pv_tv
    equity = ev - net_debt
    per_share = equity / shares_outstanding if shares_outstanding and shares_outstanding > 0 else None
    return DcfResult(
        enterprise_value=float(ev),
        pv_explicit=float(pv),
        pv_terminal=float(pv_tv),
        terminal_value=float(tv),
        implied_per_share=float(per_share) if per_share is not None else None,
        shares_outstanding=float(shares_outstanding) if shares_outstanding else None,
    )
