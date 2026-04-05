from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class StatementType(StrEnum):
    INCOME = "income"
    BALANCE = "balance"
    CASHFLOW = "cashflow"


class StatementLine(BaseModel):
    label: str
    concept: str | None = None
    fiscal_period_end: date
    value: float | None
    unit: str = "USD"
    statement_type: StatementType
