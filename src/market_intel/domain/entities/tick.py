from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TradeTick(BaseModel):
    symbol: str
    ts: datetime
    price: float = Field(..., gt=0)
    size: float = Field(default=0.0, ge=0)
    exchange: str | None = None
    conditions: list[str] | None = None
    source: Literal["polygon", "finnhub", "yfinance", "synthetic"] = "polygon"


class QuoteTick(BaseModel):
    symbol: str
    ts: datetime
    bid: float | None = None
    ask: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    source: Literal["polygon", "finnhub", "yfinance", "synthetic"] = "polygon"
