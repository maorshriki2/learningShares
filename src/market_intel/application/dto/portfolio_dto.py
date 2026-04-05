from decimal import Decimal

from pydantic import BaseModel, Field


class PositionDTO(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    last_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None


class PortfolioStateDTO(BaseModel):
    cash_usd: Decimal
    positions: list[PositionDTO]
    total_equity: float
    unrealized_pnl: float
    portfolio_beta: float
    sector_weights: dict[str, float]
