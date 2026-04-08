from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from market_intel.application.dto.governance_dto import GovernanceDashboardDTO
from market_intel.application.dto.instrument_dto import InstrumentSummaryDTO
from market_intel.application.dto.market_context_dto import MarketContextFeedDTO


class MarketOhlcvPayloadDTO(BaseModel):
    """Same shape as `/api/v1/market/{symbol}/ohlcv`."""

    symbol: str
    timeframe: str
    candles: list[dict[str, Any]] = Field(default_factory=list)
    patterns: list[dict[str, Any]] = Field(default_factory=list)
    indicators: dict[str, Any] = Field(default_factory=dict)
    fibonacci: dict[str, Any] | None = None


class ValuationVerdictDTO(BaseModel):
    """Same shape as `/api/v1/valuation/{symbol}/verdict` (stable contract)."""

    ok: bool = True
    symbol: str
    fetched_at_utc: str | None = None
    verdict: dict[str, Any] = Field(default_factory=dict)
    sanity_checks: dict[str, Any] = Field(default_factory=dict)
    ranges: dict[str, Any] = Field(default_factory=dict)
    explain: dict[str, Any] | None = None


class ChartTechnicalVerdictDTO(BaseModel):
    """Deterministic chart-only snapshot/verdict computed from OHLCV payload."""

    ok: bool = True
    symbol: str
    timeframe: str
    limit: int
    fetched_at_utc: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)
    explain: dict[str, Any] | None = None


class MarketContextVerdictDTO(BaseModel):
    """
    Minimal verdict derived from the market context feed.
    Must be present even when the feed is empty/unavailable (fail-soft).
    """

    ok: bool = True
    symbol: str
    fetched_at_utc: str | None = None
    signal: Literal["bullish", "bearish", "neutral", "not_ready"] = "not_ready"
    confidence: float | None = None
    key_points_he: list[str] = Field(default_factory=list)
    risks_he: list[str] = Field(default_factory=list)
    explain: dict[str, Any] | None = None


class Stock360ComposedDTO(BaseModel):
    """
    Stock 360 composed from (valuation + chart + context) verdicts.
    Keep traceability to both verdict-level signals and raw inputs.
    """

    ok: bool = True
    symbol: str
    fetched_at_utc: str | None = None
    final_label: Literal["buy", "hold", "sell", "watch"] = "watch"
    direction: Literal["up", "down_or_flat", "mixed", "unknown"] = "unknown"
    confidence: float | None = None
    key_reasons_he: list[str] = Field(default_factory=list)
    risks_he: list[str] = Field(default_factory=list)
    required_entry_price: float | None = None
    trace: dict[str, Any] = Field(default_factory=dict)
    explain: dict[str, Any] | None = None


class AnalysisInputsDTO(BaseModel):
    instrument_summary: InstrumentSummaryDTO | dict[str, Any] | None = None
    ohlcv: MarketOhlcvPayloadDTO | dict[str, Any] | None = None
    fundamentals: dict[str, Any] | None = None
    governance: GovernanceDashboardDTO | dict[str, Any] | None = None
    analyst_narrative: dict[str, Any] | None = None
    peers: dict[str, Any] | None = None
    market_context_feed: MarketContextFeedDTO | dict[str, Any] | None = None


class AnalysisVerdictsDTO(BaseModel):
    valuation_verdict: ValuationVerdictDTO | dict[str, Any] | None = None
    chart_technical_verdict: ChartTechnicalVerdictDTO | dict[str, Any] | None = None
    market_context_verdict: MarketContextVerdictDTO | dict[str, Any] | None = None


class AnalysisMetaDTO(BaseModel):
    artifact_version: str = "v1"
    fetched_at_utc: datetime
    missing: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class AnalysisArtifactDTO(BaseModel):
    ok: bool = True
    symbol: str
    meta: AnalysisMetaDTO
    inputs: AnalysisInputsDTO
    verdicts: AnalysisVerdictsDTO
    stock360: Stock360ComposedDTO | dict[str, Any] | None = None

