"""Two-way DCF sensitivity: WACC vs terminal growth → intrinsic per share grid."""

from __future__ import annotations

import math

from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, discounted_cash_flow_value


def build_dcf_sensitivity_matrix(
    base_free_cash_flow: float,
    shares_outstanding: float | None,
    net_debt: float,
    growth_years_1_to_5: float,
    base_wacc: float,
    base_terminal_growth: float,
    wacc_half_span: float = 0.02,
    terminal_half_span: float = 0.01,
    grid_size: int = 5,
) -> tuple[list[float], list[float], list[list[float | None]]]:
    """
    Vary WACC in [base - wacc_half_span, base + wacc_half_span] and
    terminal growth in [base - terminal_half_span, base + terminal_half_span].
    Returns (wacc_axis ascending, terminal_axis ascending, matrix[w][t] = per_share or None if invalid).
    """
    n = max(3, min(grid_size, 9))
    w_lo = max(0.001, base_wacc - wacc_half_span)
    w_hi = min(0.35, base_wacc + wacc_half_span)
    if w_lo >= w_hi:
        w_lo, w_hi = base_wacc * 0.9, base_wacc * 1.1
    t_lo = max(-0.02, base_terminal_growth - terminal_half_span)
    t_hi = min(0.06, base_terminal_growth + terminal_half_span)
    if t_lo >= t_hi:
        t_lo, t_hi = base_terminal_growth - 0.005, base_terminal_growth + 0.005

    w_vals = [w_lo + (w_hi - w_lo) * i / (n - 1) for i in range(n)]
    term_vals = [t_lo + (t_hi - t_lo) * j / (n - 1) for j in range(n)]

    matrix: list[list[float | None]] = []
    fcf = max(base_free_cash_flow, 1.0)
    for w in w_vals:
        row: list[float | None] = []
        w_eff = max(w, 0.04)
        for tg in term_vals:
            if tg >= w_eff - 0.001:
                row.append(None)
                continue
            try:
                res = discounted_cash_flow_value(
                    DcfInputs(
                        base_free_cash_flow=fcf,
                        growth_years_1_to_5=growth_years_1_to_5,
                        terminal_growth=tg,
                        wacc=w_eff,
                    ),
                    shares_outstanding=shares_outstanding,
                    net_debt=net_debt,
                )
                ps = res.implied_per_share
                row.append(float(ps) if ps is not None and math.isfinite(ps) else None)
            except (ValueError, ZeroDivisionError):
                row.append(None)
        matrix.append(row)

    return w_vals, term_vals, matrix
