from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AltmanZInputs:
    working_capital: float
    total_assets: float
    retained_earnings: float
    ebit: float
    market_value_equity: float
    total_liabilities: float
    sales: float


def altman_z_score(inp: AltmanZInputs) -> float:
    """
    Altman Z (public manufacturing variant):
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    """
    ta = inp.total_assets
    if ta <= 0:
        return float("nan")
    x1 = inp.working_capital / ta
    x2 = inp.retained_earnings / ta
    x3 = inp.ebit / ta
    tl = inp.total_liabilities if inp.total_liabilities > 0 else 1e-9
    x4 = inp.market_value_equity / tl
    x5 = inp.sales / ta
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
