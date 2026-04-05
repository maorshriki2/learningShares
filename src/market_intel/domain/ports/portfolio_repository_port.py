from typing import Protocol

from market_intel.domain.entities.portfolio import Portfolio


class PortfolioRepositoryPort(Protocol):
    async def load(self) -> Portfolio: ...

    async def save(self, portfolio: Portfolio) -> None: ...
