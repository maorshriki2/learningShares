from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PiotroskiYearSnapshot:
    net_income: float
    operating_cash_flow: float
    roa: float
    long_term_debt: float
    current_ratio: float
    shares_outstanding: float
    gross_margin: float
    asset_turnover: float


@dataclass(frozen=True)
class PiotroskiInput:
    current: PiotroskiYearSnapshot
    prior: PiotroskiYearSnapshot


def piotroski_f_score(inp: PiotroskiInput) -> tuple[int, dict[str, int]]:
    """
    Classic 9-point F-Score using two consecutive fiscal snapshots.
    ROA, CFO, long-term debt, liquidity, dilution, margin, turnover vs prior.
    """
    c, p = inp.current, inp.prior
    flags: dict[str, int] = {}

    flags["positive_net_income"] = 1 if c.net_income > 0 else 0
    flags["positive_cfo"] = 1 if c.operating_cash_flow > 0 else 0
    flags["cfo_exceeds_ni"] = 1 if c.operating_cash_flow > c.net_income else 0

    flags["improving_roa"] = 1 if c.roa > p.roa else 0

    flags["lower_long_term_debt"] = 1 if c.long_term_debt < p.long_term_debt else 0
    flags["improving_current_ratio"] = 1 if c.current_ratio > p.current_ratio else 0
    flags["no_new_shares"] = 1 if c.shares_outstanding <= p.shares_outstanding else 0

    flags["improving_gross_margin"] = 1 if c.gross_margin > p.gross_margin else 0
    flags["improving_asset_turnover"] = 1 if c.asset_turnover > p.asset_turnover else 0

    total = int(sum(flags.values()))
    return total, flags
