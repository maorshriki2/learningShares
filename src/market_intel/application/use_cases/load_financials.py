from __future__ import annotations

from market_intel.application.dto.fundamentals_dto import FundamentalsDashboardDTO
from market_intel.application.services.fundamentals_service import FundamentalsService


async def load_financial_dashboard(
    service: FundamentalsService,
    symbol: str,
    years: int = 10,
) -> FundamentalsDashboardDTO:
    return await service.build_dashboard(symbol, years)
