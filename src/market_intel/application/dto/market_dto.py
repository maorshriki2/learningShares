from datetime import datetime

from pydantic import BaseModel, Field


class TickDTO(BaseModel):
    symbol: str
    ts: datetime
    price: float
    size: float = 0.0
    source: str = "polygon"


class CandleDTO(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class PatternDTO(BaseModel):
    name: str
    start_index: int
    end_index: int
    confidence: float
    meta: dict[str, object] = Field(default_factory=dict)
