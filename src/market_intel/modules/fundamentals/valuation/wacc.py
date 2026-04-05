from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WaccInputs:
    cost_of_equity: float
    cost_of_debt_after_tax: float
    equity_market_value: float
    debt_book_value: float
    tax_rate: float


def estimate_wacc(inputs: WaccInputs) -> float:
    """
    WACC = (E/V)*Re + (D/V)*Rd*(1-T)
    Here cost_of_debt_after_tax should already include (1-T) if desired; we apply weights only.
    """
    e = max(inputs.equity_market_value, 0.0)
    d = max(inputs.debt_book_value, 0.0)
    v = e + d
    if v <= 0:
        return max(inputs.cost_of_equity, 0.0)
    return (e / v) * inputs.cost_of_equity + (d / v) * inputs.cost_of_debt_after_tax
