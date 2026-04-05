import re

from pydantic import BaseModel, Field, field_validator


class Symbol(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        t = v.strip().upper()
        if not re.match(r"^[A-Z0-9.\-]+$", t):
            raise ValueError("Invalid ticker format")
        return t
