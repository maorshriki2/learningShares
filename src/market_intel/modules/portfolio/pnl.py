from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from market_intel.domain.entities.portfolio import Portfolio


@dataclass(frozen=True)
class PositionMark:
    symbol: str
    quantity: float
    avg_cost: float
    last_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pct: float


@dataclass(frozen=True)
class PortfolioMark:
    cash_usd: Decimal
    positions: list[PositionMark]
    total_equity: Decimal
    unrealized_pnl: float


def mark_portfolio(portfolio: Portfolio, prices: dict[str, float]) -> PortfolioMark:
    marks: list[PositionMark] = []
    unrealized = 0.0
    equity = float(portfolio.cash_usd)
    for sym, pos in portfolio.positions.items():
        px = prices.get(sym)
        if px is None:
            continue
        mv = pos.quantity * px
        cost_basis = pos.quantity * pos.avg_cost
        pnl = mv - cost_basis
        unrealized += pnl
        equity += mv
        pct = (pnl / cost_basis * 100.0) if cost_basis else 0.0
        marks.append(
            PositionMark(
                symbol=sym,
                quantity=pos.quantity,
                avg_cost=pos.avg_cost,
                last_price=px,
                market_value=mv,
                unrealized_pnl=pnl,
                unrealized_pct=pct,
            )
        )
    return PortfolioMark(
        cash_usd=portfolio.cash_usd,
        positions=marks,
        total_equity=Decimal(str(equity)),
        unrealized_pnl=unrealized,
    )
