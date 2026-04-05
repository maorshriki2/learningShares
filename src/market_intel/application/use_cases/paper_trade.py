from __future__ import annotations

from market_intel.application.services.portfolio_service import PortfolioService
from market_intel.domain.entities.portfolio import Portfolio


async def paper_buy(
    service: PortfolioService,
    symbol: str,
    qty: float,
    price: float,
) -> Portfolio:
    return await service.buy(symbol, qty, price)


async def paper_sell(
    service: PortfolioService,
    symbol: str,
    qty: float,
    price: float,
) -> Portfolio:
    return await service.sell(symbol, qty, price)
