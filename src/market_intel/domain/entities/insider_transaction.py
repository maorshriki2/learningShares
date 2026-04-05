from datetime import date

from pydantic import BaseModel, Field


class InsiderTransaction(BaseModel):
    symbol: str
    insider_name: str
    insider_title: str | None = None
    transaction_type: str
    shares: float
    price_per_share: float | None = None
    value_usd: float | None = None
    transaction_date: date
    filing_date: date
    ownership_nature: str | None = None
