from datetime import date

from pydantic import BaseModel, Field

from market_intel.domain.ports.sentiment_port import SentenceSentiment


class FilingDTO(BaseModel):
    form: str
    filed: date
    url: str | None


class InsiderRowDTO(BaseModel):
    insider_name: str
    transaction_type: str
    shares: float
    transaction_date: date


class GovernanceDashboardDTO(BaseModel):
    symbol: str
    filings_8k: list[FilingDTO]
    insider_summary_buy: int
    insider_summary_sell: int
    insider_net_shares: float
    insider_rows: list[InsiderRowDTO]
    executives: list[dict[str, object]]
    transcript_snippets: list[str]
    highlights_bullish: list[SentenceSentiment]
    highlights_bearish: list[SentenceSentiment]
    corporate_speak_lesson: str
    explain: dict[str, object] = Field(default_factory=dict)
