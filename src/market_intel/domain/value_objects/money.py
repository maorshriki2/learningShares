from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, field_validator


class Money(BaseModel):
    amount: Decimal = Field(..., description="Monetary amount")
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    def __add__(self, other: Self) -> Self:
        if not isinstance(other, Money) or self.currency != other.currency:
            raise TypeError("Cannot add Money with different currencies or types")
        return self.model_copy(update={"amount": self.amount + other.amount})

    def __sub__(self, other: Self) -> Self:
        if not isinstance(other, Money) or self.currency != other.currency:
            raise TypeError("Cannot subtract Money with different currencies or types")
        return self.model_copy(update={"amount": self.amount - other.amount})

    def __mul__(self, factor: Decimal | float | int) -> Self:
        f = Decimal(str(factor))
        return self.model_copy(update={"amount": (self.amount * f).quantize(Decimal("0.0001"))})
