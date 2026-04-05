from __future__ import annotations

from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, discounted_cash_flow_value


def run_dcf_scenario(
    base_fcf: float,
    growth: float,
    terminal_growth: float,
    wacc: float,
    shares_outstanding: float | None,
    net_debt: float,
) -> object:
    return discounted_cash_flow_value(
        DcfInputs(
            base_free_cash_flow=max(base_fcf, 1.0),
            growth_years_1_to_5=growth,
            terminal_growth=terminal_growth,
            wacc=max(wacc, 0.04),
        ),
        shares_outstanding=shares_outstanding,
        net_debt=net_debt,
    )
