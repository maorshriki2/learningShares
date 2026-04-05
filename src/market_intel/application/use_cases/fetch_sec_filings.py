from __future__ import annotations

from market_intel.domain.entities.filing import FilingRecord
from market_intel.infrastructure.sec.sec_edgar_adapter import SecEdgarHttpAdapter


async def fetch_recent_filings(
    sec: SecEdgarHttpAdapter,
    symbol: str,
    forms: list[str],
    limit: int,
) -> list[FilingRecord]:
    return await sec.recent_filings(symbol, forms, limit)
