from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PatternAnnotation(BaseModel):
    name: str
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    meta: dict[str, Any] = Field(default_factory=dict)
    start_time: datetime | None = None
    end_time: datetime | None = None
