from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from market_intel.domain.entities.position import Position


class Portfolio(BaseModel):
    cash_usd: Decimal = Field(default=Decimal("100000"))
    positions: dict[str, Position] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("cash_usd", mode="before")
    @classmethod
    def coerce_decimal(cls, v: object) -> Decimal:
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))
