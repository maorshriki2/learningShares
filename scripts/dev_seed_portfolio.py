from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from market_intel.config.settings import get_settings
from market_intel.domain.entities.portfolio import Portfolio
from market_intel.infrastructure.persistence.json_portfolio_repo import JsonPortfolioRepository


async def main() -> None:
    settings = get_settings()
    repo = JsonPortfolioRepository(settings)
    p = Portfolio(cash_usd=Decimal("95000"), positions={})
    await repo.save(p)
    print(f"Wrote seed portfolio to {settings.portfolio_storage_path}")


if __name__ == "__main__":
    asyncio.run(main())
