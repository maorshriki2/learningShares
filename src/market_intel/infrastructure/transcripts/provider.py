from __future__ import annotations

import json
from typing import Any

import httpx

from market_intel.config.settings import Settings
from market_intel.domain.ports.transcript_port import (
    EarningsTranscript,
    TranscriptPort,
    TranscriptUtterance,
)
from market_intel.infrastructure.cache.redis_cache import MemoryCache, RedisCache, cache_key
from market_intel.modules.governance.earnings_transcript import split_into_sentences


class FinnhubTranscriptAdapter(TranscriptPort):
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache

    async def fetch_transcript(self, symbol: str, year: int, quarter: int) -> EarningsTranscript | None:
        if not self._settings.finnhub_api_key:
            text = self._synthetic_transcript(symbol, year, quarter)
            return utterances_from_blocks(symbol, year, quarter, text, source="synthetic")

        ck = cache_key("fh:transcript", {"s": symbol.upper(), "y": year, "q": quarter})
        cached = await self._cache.get(ck)
        if cached:
            try:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8", errors="ignore")
                text = str(cached).strip()
                if text:
                    data = json.loads(text)
                    return EarningsTranscript.model_validate(data)
            except Exception:
                pass

        url = "https://finnhub.io/api/v1/stock/earnings-call-transcript"
        params = {
            "symbol": symbol.upper(),
            "year": year,
            "quarter": quarter,
            "token": self._settings.finnhub_api_key,
        }
        r = await self._client.get(url, params=params, timeout=30.0)
        if r.status_code != 200:
            text = self._synthetic_transcript(symbol, year, quarter)
            return utterances_from_blocks(symbol, year, quarter, text, source="fallback")
        try:
            payload: Any = r.json()
        except (json.JSONDecodeError, ValueError):
            text = self._synthetic_transcript(symbol, year, quarter)
            return utterances_from_blocks(symbol, year, quarter, text, source="fallback")
        raw_text = self._extract_text(payload)
        if not raw_text:
            text = self._synthetic_transcript(symbol, year, quarter)
            tr = utterances_from_blocks(symbol, year, quarter, text, source="fallback")
        else:
            tr = utterances_from_plaintext(symbol, year, quarter, raw_text, source="finnhub")
        await self._cache.set(ck, tr.model_dump_json(), ttl_seconds=86400)
        return tr

    def _extract_text(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, list) and payload:
            parts: list[str] = []
            for row in payload:
                if isinstance(row, dict):
                    for key in ("text", "content", "speech", "line"):
                        v = row.get(key)
                        if isinstance(v, str):
                            parts.append(v)
                elif isinstance(row, str):
                    parts.append(row)
            return "\n".join(parts)
        if isinstance(payload, dict):
            for key in ("transcript", "text", "data"):
                v = payload.get(key)
                if isinstance(v, str):
                    return v
                if isinstance(v, list):
                    return self._extract_text(v)
        return ""

    def _synthetic_transcript(self, symbol: str, year: int, quarter: int) -> str:
        return (
            f"Welcome to the {symbol.upper()} earnings call for Q{quarter} {year}. "
            "We delivered solid execution this quarter with disciplined cost control. "
            "We remain cautiously optimistic on demand trends while navigating macro headwinds. "
            "Our balance sheet is strong and we continue to invest in long-term growth initiatives. "
            "We expect margins to improve as mix shifts toward higher-value offerings."
        )


def utterances_from_plaintext(
    symbol: str,
    year: int,
    quarter: int,
    body: str,
    source: str,
) -> EarningsTranscript:
    sents = split_into_sentences(body)
    utt = [TranscriptUtterance(speaker="Management", text=s, sequence=i) for i, s in enumerate(sents)]
    return EarningsTranscript(symbol=symbol.upper(), year=year, quarter=quarter, source=source, utterances=utt)


def utterances_from_blocks(
    symbol: str,
    year: int,
    quarter: int,
    body: str,
    source: str,
) -> EarningsTranscript:
    return utterances_from_plaintext(symbol, year, quarter, body, source=source)
