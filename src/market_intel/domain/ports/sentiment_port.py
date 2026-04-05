from typing import Protocol

from pydantic import BaseModel, Field


class SentenceSentiment(BaseModel):
    text: str
    label: str
    score_positive: float = Field(ge=0.0, le=1.0)
    score_negative: float = Field(ge=0.0, le=1.0)
    score_neutral: float = Field(ge=0.0, le=1.0)


class SentimentPort(Protocol):
    async def score_sentences(self, sentences: list[str]) -> list[SentenceSentiment]: ...
