from typing import AsyncIterator, Protocol

from market_intel.domain.entities.tick import QuoteTick, TradeTick


class WebSocketMarketPort(Protocol):
    async def stream_trades(self, symbol: str) -> AsyncIterator[TradeTick]: ...

    async def stream_quotes(self, symbol: str) -> AsyncIterator[QuoteTick]: ...
