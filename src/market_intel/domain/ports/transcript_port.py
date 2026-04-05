from typing import Protocol

from pydantic import BaseModel, Field


class TranscriptUtterance(BaseModel):
    speaker: str
    text: str
    sequence: int = Field(ge=0)


class EarningsTranscript(BaseModel):
    symbol: str
    year: int
    quarter: int
    source: str
    utterances: list[TranscriptUtterance]


class TranscriptPort(Protocol):
    async def fetch_transcript(self, symbol: str, year: int, quarter: int) -> EarningsTranscript | None: ...
