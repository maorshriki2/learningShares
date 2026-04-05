from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from market_intel.domain.entities.portfolio import Portfolio
from market_intel.domain.entities.position import Position


class PaperTradingEngine:
    def __init__(self, portfolio: Portfolio) -> None:
        self._portfolio = portfolio

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio

    def buy(self, symbol: str, quantity: float, price: float) -> Portfolio:
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        cost = Decimal(str(quantity * price))
        if self._portfolio.cash_usd < cost:
            raise ValueError("Insufficient cash for purchase")
        self._portfolio.cash_usd -= cost
        sym = symbol.upper()
        now = datetime.now(timezone.utc)
        existing = self._portfolio.positions.get(sym)
        if existing:
            total_qty = existing.quantity + quantity
            new_avg = (
                existing.quantity * existing.avg_cost + quantity * price
            ) / total_qty
            self._portfolio.positions[sym] = Position(
                symbol=sym,
                quantity=total_qty,
                avg_cost=new_avg,
                opened_at=existing.opened_at,
            )
        else:
            self._portfolio.positions[sym] = Position(
                symbol=sym,
                quantity=quantity,
                avg_cost=price,
                opened_at=now,
            )
        self._portfolio.updated_at = now
        return self._portfolio

    def sell(self, symbol: str, quantity: float, price: float) -> Portfolio:
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        sym = symbol.upper()
        pos = self._portfolio.positions.get(sym)
        if not pos or pos.quantity < quantity:
            raise ValueError("Cannot sell more than owned")
        proceeds = Decimal(str(quantity * price))
        self._portfolio.cash_usd += proceeds
        remaining = pos.quantity - quantity
        if remaining <= 1e-9:
            del self._portfolio.positions[sym]
        else:
            self._portfolio.positions[sym] = Position(
                symbol=sym,
                quantity=remaining,
                avg_cost=pos.avg_cost,
                opened_at=pos.opened_at,
            )
        self._portfolio.updated_at = datetime.now(timezone.utc)
        return self._portfolio
