from datetime import datetime

from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str
    quantity: float = Field(..., description="Shares held (can be fractional for demo)")
    avg_cost: float = Field(..., gt=0)
    opened_at: datetime
