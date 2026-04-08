from __future__ import annotations

import json
import re
from typing import Any

import httpx

from market_intel.application.dto.governance_dto import (
    FilingDTO,
    GovernanceDashboardDTO,
    InsiderRowDTO,
)
from market_intel.config.settings import Settings
from market_intel.domain.ports.sentiment_port import SentimentPort
from market_intel.domain.ports.transcript_port import TranscriptPort
from market_intel.infrastructure.market_data.instrument_info import executives_from_yfinance
from market_intel.infrastructure.nlp.sentence_highlight import top_bullish_bearish
from market_intel.infrastructure.sec.sec_edgar_adapter import SecEdgarHttpAdapter
from market_intel.modules.governance.corporate_speak_education import corporate_speak_lesson
from market_intel.modules.governance.insider_aggregation import aggregate_insider_transactions


class GovernanceService:
    def __init__(
        self,
        sec: SecEdgarHttpAdapter,
        transcripts: TranscriptPort,
        sentiment: SentimentPort,
        settings: Settings,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._sec = sec
        self._transcripts = transcripts
        self._sentiment = sentiment
        self._settings = settings
        self._http = http_client

    async def build_dashboard(
        self,
        symbol: str,
        year: int,
        quarter: int,
    ) -> GovernanceDashboardDTO:
        try:
            filings_8k = await self._sec.recent_filings(symbol, ["8-K"], limit=8)
        except Exception:
            filings_8k = []
        try:
            insider_rows = await self._sec.insider_form4_recent(symbol, limit=25)
        except Exception:
            insider_rows = []
        summary = aggregate_insider_transactions(insider_rows)
        try:
            execs = await executives_from_yfinance(symbol)
        except Exception:
            execs = []

        try:
            transcript = await self._transcripts.fetch_transcript(symbol, year, quarter)
        except Exception:
            transcript = None
        sentences = [u.text for u in (transcript.utterances if transcript else []) if u.text]
        scored_limit = 40
        try:
            scored = await self._sentiment.score_sentences(sentences[:scored_limit])
        except Exception:
            scored = []
        highlight_k = 5
        bull, bear = top_bullish_bearish(scored, k=highlight_k)
        lesson = corporate_speak_lesson(bull + bear)
        return GovernanceDashboardDTO(
            symbol=symbol.upper(),
            filings_8k=[
                FilingDTO(form=f.form, filed=f.filed, url=str(f.filing_url) if f.filing_url else None)
                for f in filings_8k
            ],
            insider_summary_buy=summary.buy_count,
            insider_summary_sell=summary.sell_count,
            insider_net_shares=summary.net_shares,
            insider_rows=[
                InsiderRowDTO(
                    insider_name=r.insider_name,
                    transaction_type=r.transaction_type,
                    shares=r.shares,
                    transaction_date=r.transaction_date,
                )
                for r in insider_rows[:15]
            ],
            executives=[e.model_dump() for e in execs[:8]],
            transcript_snippets=sentences[:12],
            highlights_bullish=bull,
            highlights_bearish=bear,
            corporate_speak_lesson=lesson,
            explain={
                "transcript_source": getattr(transcript, "source", None) if transcript else None,
                "year": int(year),
                "quarter": int(quarter),
                "sentences_total": int(len(sentences)),
                "sentences_scored": int(min(len(sentences), scored_limit)),
                "sentences_scoring_limit": int(scored_limit),
                "highlights_k": int(highlight_k),
                "highlight_selection": "top_bullish_bearish(scored, k=5) from FinBERT sentence scores",
                "notes": [
                    "Only first N sentences are scored for latency/cost control.",
                    "Highlights are educational; sentiment labels are model outputs, not facts.",
                ],
            },
        )

    async def analyst_narrative(self, symbol: str, year: int, quarter: int) -> dict[str, Any]:
        """
        Claude summary over earnings call transcript (Finnhub / synthetic) + prior quarter for tone delta.
        """
        sym = symbol.upper()
        cur = None
        prev = None
        try:
            cur = await self._transcripts.fetch_transcript(sym, year, quarter)
        except Exception:
            cur = None
        py, pq = (year, quarter - 1) if quarter > 1 else (year - 1, 4)
        try:
            prev = await self._transcripts.fetch_transcript(sym, py, pq)
        except Exception:
            prev = None

        def _flatten(tr: object | None, max_chars: int) -> str:
            if tr is None:
                return ""
            ut = getattr(tr, "utterances", None) or []
            parts = [u.text for u in ut if getattr(u, "text", None)]
            body = " ".join(parts)
            return body[:max_chars]

        text_cur = _flatten(cur, 24_000)
        text_prev = _flatten(prev, 12_000)
        source = getattr(cur, "source", None) if cur else None
        meta = {
            "symbol": sym,
            "year": int(year),
            "quarter": int(quarter),
            "source": source or "unknown",
            "anthropic_model": self._settings.anthropic_model,
            "truncation_chars": {"current": 24_000, "prior": 12_000},
            "json_extraction": "regex first {...} block from model text, then json.loads",
        }

        if not self._settings.anthropic_api_key:
            return {
                "ok": False,
                "source": source or "unknown",
                "meta": meta,
                "message_he": "הגדר ANTHROPIC_API_KEY ב־.env כדי לקבל ניתוח נרטיבי אוטומטי (Claude). בינתיים ניתן לקרוא את קטעי הטרנסקריפט בלשונית הראשית.",
                "strengths_he": [],
                "risks_hedged_he": [],
                "sentiment_vs_prior_he": "לא זמין ללא מפתח API.",
            }

        if not text_cur.strip():
            return {
                "ok": False,
                "source": source or "unknown",
                "meta": meta,
                "message_he": "לא נמצא טקסט מספיק בטרנסקריפט לרבעון הזה.",
                "strengths_he": [],
                "risks_hedged_he": [],
                "sentiment_vs_prior_he": "—",
            }

        prompt = f"""אתה אנליסט שוק הון. קרא את טקסט שיחת הרווחים (אנגלית) של {sym} לרבעון {year} Q{quarter}.
להלן קטע מהרבעון הנוכחי:
---
{text_cur}
---
ולהשוואה, קטע קצר יותר מהרבעון הקודם ({py} Q{pq}):
---
{text_prev}
---
החזר **רק** JSON תקין (בלי markdown) במבנה:
{{"strengths_he":["נקודה1","נקודה2","נקודה3"],"risks_hedged_he":["סיכון1","סיכון2","סיכון3"],"sentiment_vs_prior_he":"פסקה קצרה בעברית המשווה טון ושקיפות מול הרבעון הקודם"}}

strengths_he = שלוש נקודות חוזק שההנהלה הדגישה (בעברית).
risks_hedged_he = שלושה סיכונים או נושאים שההנהלה התחמקה מהם או ניסחה בזהירות (בעברית).
sentiment_vs_prior_he = שינוי בסנטימנט/בהירות לעומת הרבעון הקודם (בעברית)."""

        try:
            r = await self._http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._settings.anthropic_model,
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120.0,
            )
            r.raise_for_status()
            payload = r.json()
            blocks = payload.get("content") or []
            raw = ""
            for b in blocks:
                if isinstance(b, dict) and b.get("type") == "text":
                    raw += str(b.get("text", ""))
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                raise ValueError("no json in claude response")
            data = json.loads(m.group(0))
            return {
                "ok": True,
                "source": source or "unknown",
                "meta": meta,
                "strengths_he": list(data.get("strengths_he") or [])[:5],
                "risks_hedged_he": list(data.get("risks_hedged_he") or [])[:5],
                "sentiment_vs_prior_he": str(data.get("sentiment_vs_prior_he") or ""),
                "message_he": "",
            }
        except Exception as exc:
            return {
                "ok": False,
                "source": source or "unknown",
                "meta": meta,
                "message_he": f"שגיאה בקריאה ל־Claude: {exc}",
                "strengths_he": [],
                "risks_hedged_he": [],
                "sentiment_vs_prior_he": "—",
            }
