from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MarketContextItemDTO(BaseModel):
    id: str
    source: str
    tier: int = Field(ge=1, le=3)
    title: str
    url: str | None = None
    occurred_at: datetime | None = None
    summary: str | None = None
    summary_he: str | None = None
    tags: list[str] = Field(default_factory=list)
    sentiment_label: str | None = None  # negative|neutral|positive
    sentiment_score: float | None = None
    relevance: float | None = None  # 0..1 after time decay


class MarketContextSectionDTO(BaseModel):
    id: str
    title: str | None = None
    title_he: str | None = None
    subtitle: str | None = None
    subtitle_he: str | None = None
    ai_bottom_line: str | None = None
    ai_bottom_line_he: str | None = None
    ai_verdict: str | None = None  # bullish|bearish|mixed
    ai_debug: dict[str, int] | None = None
    items: list[MarketContextItemDTO] = Field(default_factory=list)


class MarketContextFeedDTO(BaseModel):
    ok: bool = True
    symbol: str
    fetched_at_utc: datetime | None = None
    as_of: datetime | None = None
    message: str | None = None
    message_he: str | None = None
    sources_attempted: list[str] = Field(default_factory=list)
    errors: list[dict[str, object]] = Field(default_factory=list)
    sections: list[MarketContextSectionDTO] = Field(default_factory=list)
