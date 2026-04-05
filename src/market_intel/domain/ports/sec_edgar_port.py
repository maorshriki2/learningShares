from typing import Protocol

from market_intel.domain.entities.filing import FilingRecord
from market_intel.domain.entities.insider_transaction import InsiderTransaction


class SecEdgarPort(Protocol):
    async def resolve_cik(self, symbol: str) -> str: ...

    async def recent_filings(self, symbol: str, forms: list[str], limit: int) -> list[FilingRecord]: ...

    async def insider_form4_recent(self, symbol: str, limit: int) -> list[InsiderTransaction]: ...
