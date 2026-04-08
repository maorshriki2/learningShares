from __future__ import annotations

from pydantic import BaseModel


class InstrumentSummaryDTO(BaseModel):
    symbol: str
    name: str | None = None
    sector: str | None = None
    market_cap: float | None = None
    price: float | None = None
    beta: float | None = None
    volatility_1y: float | None = None

