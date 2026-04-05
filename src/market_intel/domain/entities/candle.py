from datetime import datetime

from pydantic import BaseModel, Field

from market_intel.domain.value_objects.timeframe import Timeframe


class Candle(BaseModel):
    symbol: str
    timeframe: Timeframe
    ts: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(default=0.0, ge=0)
