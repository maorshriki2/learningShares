from __future__ import annotations

from dataclasses import dataclass

from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, DcfResult, discounted_cash_flow_value
from market_intel.modules.fundamentals.valuation.wacc import WaccInputs, estimate_wacc


@dataclass(frozen=True)
class RateScenario:
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    cost_of_debt_pretax: float
    tax_rate: float
    equity_weight: float
    debt_weight: float
    base_fcf: float
    growth: float
    terminal_growth: float
    shares_outstanding: float | None
    net_debt: float


@dataclass(frozen=True)
class ScenarioResult:
    risk_free_rate: float
    wacc: float
    cost_of_equity: float
    implied_per_share: float | None
    enterprise_value: float
    pv_explicit: float
    pv_terminal: float


def simulate_wacc_rate_impact(
    scenario: RateScenario,
    rate_deltas: list[float] | None = None,
) -> list[ScenarioResult]:
    if rate_deltas is None:
        rate_deltas = [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0]

    results: list[ScenarioResult] = []
    for delta in rate_deltas:
        rfr = max(0.001, scenario.risk_free_rate + delta / 100.0)
        cost_eq = rfr + scenario.equity_risk_premium * scenario.beta
        cost_debt = scenario.cost_of_debt_pretax * (1.0 - scenario.tax_rate)
        wacc = estimate_wacc(
            WaccInputs(
                cost_of_equity=cost_eq,
                cost_of_debt_after_tax=cost_debt,
                equity_market_value=max(scenario.equity_weight, 0.001),
                debt_book_value=max(scenario.debt_weight, 0.0),
                tax_rate=scenario.tax_rate,
            )
        )
        tg = min(scenario.terminal_growth, wacc - 0.001)
        dcf = discounted_cash_flow_value(
            DcfInputs(
                base_free_cash_flow=max(scenario.base_fcf, 1.0),
                growth_years_1_to_5=scenario.growth,
                terminal_growth=tg,
                wacc=max(wacc, 0.03),
            ),
            shares_outstanding=scenario.shares_outstanding,
            net_debt=scenario.net_debt,
        )
        results.append(
            ScenarioResult(
                risk_free_rate=rfr,
                wacc=wacc,
                cost_of_equity=cost_eq,
                implied_per_share=dcf.implied_per_share,
                enterprise_value=dcf.enterprise_value,
                pv_explicit=dcf.pv_explicit,
                pv_terminal=dcf.pv_terminal,
            )
        )
    return results
