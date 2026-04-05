from pydantic import BaseModel, Field


class ExecutiveProfile(BaseModel):
    symbol: str
    name: str
    title: str
    tenure_years: float | None = None
    total_comp_usd: float | None = None
    salary_usd: float | None = None
    bonus_usd: float | None = None
    stock_awards_usd: float | None = None
    option_awards_usd: float | None = None
    notes: str | None = None
