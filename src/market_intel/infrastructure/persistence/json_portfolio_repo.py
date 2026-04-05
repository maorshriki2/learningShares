from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import aiofiles

from market_intel.config.settings import Settings
from market_intel.domain.entities.portfolio import Portfolio
from market_intel.domain.entities.position import Position
from market_intel.domain.ports.portfolio_repository_port import PortfolioRepositoryPort


class JsonPortfolioRepository(PortfolioRepositoryPort):
    def __init__(self, settings: Settings) -> None:
        self._path = Path(settings.portfolio_storage_path)

    async def load(self) -> Portfolio:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            p = Portfolio()
            await self.save(p)
            return p
        async with aiofiles.open(self._path, encoding="utf-8") as f:
            raw = await f.read()
        data = json.loads(raw)
        positions: dict[str, Position] = {}
        for sym, row in (data.get("positions") or {}).items():
            positions[sym] = Position(
                symbol=row["symbol"],
                quantity=float(row["quantity"]),
                avg_cost=float(row["avg_cost"]),
                opened_at=datetime.fromisoformat(row["opened_at"]),
            )
        return Portfolio(
            cash_usd=Decimal(str(data.get("cash_usd", "100000"))),
            positions=positions,
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
        )

    async def save(self, portfolio: Portfolio) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cash_usd": str(portfolio.cash_usd),
            "positions": {
                sym: {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                    "opened_at": pos.opened_at.isoformat(),
                }
                for sym, pos in portfolio.positions.items()
            },
            "updated_at": portfolio.updated_at.isoformat(),
        }
        async with aiofiles.open(self._path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(payload, indent=2))
