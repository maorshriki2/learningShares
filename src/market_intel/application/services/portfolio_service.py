from __future__ import annotations

import asyncio

import yfinance as yf

from market_intel.application.dto.portfolio_dto import PortfolioStateDTO, PositionDTO
from market_intel.domain.entities.portfolio import Portfolio
from market_intel.domain.ports.portfolio_repository_port import PortfolioRepositoryPort
from market_intel.modules.portfolio.beta import portfolio_beta
from market_intel.modules.portfolio.engine import PaperTradingEngine
from market_intel.modules.portfolio.pnl import mark_portfolio
from market_intel.modules.portfolio.sector_allocation import sector_weights
from market_intel.domain.value_objects.sector import Sector
from market_intel.infrastructure.market_data.instrument_info import SECTOR_MAP


class PortfolioService:
    def __init__(self, repo: PortfolioRepositoryPort) -> None:
        self._repo = repo

    async def load(self) -> Portfolio:
        return await self._repo.load()

    async def save(self, portfolio: Portfolio) -> None:
        await self._repo.save(portfolio)

    async def buy(self, symbol: str, qty: float, price: float) -> Portfolio:
        p = await self.load()
        engine = PaperTradingEngine(p)
        engine.buy(symbol, qty, price)
        await self.save(engine.portfolio)
        return engine.portfolio

    async def sell(self, symbol: str, qty: float, price: float) -> Portfolio:
        p = await self.load()
        engine = PaperTradingEngine(p)
        engine.sell(symbol, qty, price)
        await self.save(engine.portfolio)
        return engine.portfolio

    async def snapshot(self, portfolio: Portfolio) -> PortfolioStateDTO:
        symbols = list(portfolio.positions.keys())

        def _prices_and_betas() -> tuple[dict[str, float], dict[str, float], dict[str, Sector]]:
            px: dict[str, float] = {}
            bt: dict[str, float] = {}
            sec: dict[str, Sector] = {}
            for sym in symbols:
                t = yf.Ticker(sym)
                fi = t.fast_info
                p = fi.get("last_price") or fi.get("regular_market_price")
                if p is not None:
                    px[sym] = float(p)
                b = (t.info or {}).get("beta")
                bt[sym] = float(b) if b is not None else 1.0
                sector_raw = str((t.info or {}).get("sector") or "")
                sec[sym] = SECTOR_MAP.get(sector_raw, Sector.UNKNOWN)
            return px, bt, sec

        prices, betas, sectors = await asyncio.to_thread(_prices_and_betas)
        mark = mark_portfolio(portfolio, prices)
        w = {m.symbol: m.market_value for m in mark.positions if m.market_value > 0}
        p_beta = portfolio_beta(w, betas)
        sw = sector_weights(portfolio, prices, sectors)
        pos_dto = [
            PositionDTO(
                symbol=m.symbol,
                quantity=m.quantity,
                avg_cost=m.avg_cost,
                last_price=m.last_price,
                market_value=m.market_value,
                unrealized_pnl=m.unrealized_pnl,
            )
            for m in mark.positions
        ]
        return PortfolioStateDTO(
            cash_usd=portfolio.cash_usd,
            positions=pos_dto,
            total_equity=float(mark.total_equity),
            unrealized_pnl=mark.unrealized_pnl,
            portfolio_beta=float(p_beta),
            sector_weights=sw,
        )
