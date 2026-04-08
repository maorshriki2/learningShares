from __future__ import annotations

import asyncio
import functools
import json
import re
from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from market_intel.application.dto.market_context_dto import (
    MarketContextFeedDTO,
    MarketContextItemDTO,
    MarketContextSectionDTO,
)
from market_intel.domain.ports.sentiment_port import SentimentPort
from market_intel.config.settings import Settings
from market_intel.infrastructure.market_context.social_scrapers import Tier3SocialSentimentProvider
from market_intel.infrastructure.market_context.providers import (
    FmpProvider,
    NewsApiProvider,
    RawContextItem,
    YFinanceNewsProvider,
)
from market_intel.modules.market_context.processing import categorize_and_tag, time_decay_relevance
from market_intel.infrastructure.sec.sec_edgar_adapter import SecEdgarHttpAdapter
import httpx


class MarketContextService:
    _SOCIAL_MAX_POSTS_PER_ACCOUNT: int = 4  # must stay in [3..5]
    _SOCIAL_AI_MAX_CHARS: int = 10_000
    _SOCIAL_GATE_MAX_BORDERLINE: int = 24
    _SOCIAL_GATE_MAX_CHARS_PER_POST: int = 600
    _SOCIAL_GATE_MAX_MACRO_DIRECT: int = 10

    _STOP_TOKENS: frozenset[str] = frozenset(
        {
            "inc",
            "inc.",
            "corp",
            "corp.",
            "co",
            "co.",
            "ltd",
            "ltd.",
            "plc",
            "the",
            "and",
            "of",
            "for",
            "a",
            "an",
            "to",
            "in",
            "on",
            "at",
            "with",
            "from",
            "group",
            "holdings",
            "company",
        }
    )

    _MACRO_RX: re.Pattern[str] = re.compile(
        r"\b("
        r"fed|fomc|powell|rate\s*hike|rate\s*cut|interest\s*rate|"
        r"cpi|ppi|inflation|jobs|nfp|unemployment|"
        r"treasury|yields?|2y|10y|curve|recession|"
        r"tariff|sanctions?|war|geopolitic|china|"
        r"oil|crude|opec|brent|wti|"
        r"credit\s*spread|bank\s*run|liquidity"
        r")\b",
        re.I,
    )

    _HIGH_SIGNAL_RX: re.Pattern[str] = re.compile(r"\b(breaking|just\s+in|headline|alert|urgent)\b", re.I)

    def __init__(
        self,
        *,
        sec: SecEdgarHttpAdapter,
        finbert: SentimentPort,
        settings: Settings,
        http_client: httpx.AsyncClient,
        fmp: FmpProvider,
        newsapi: NewsApiProvider,
        social: Tier3SocialSentimentProvider,
        yfinance_news: YFinanceNewsProvider,
    ) -> None:
        self._sec = sec
        self._finbert = finbert
        self._settings = settings
        self._http = http_client
        self._fmp = fmp
        self._newsapi = newsapi
        self._social = social
        self._yfn = yfinance_news

    @staticmethod
    def _strip_urls_and_html(text: str) -> str:
        """
        Defensive text cleaning before LLM:
        - remove http/https URLs
        - remove raw HTML tags
        - collapse excessive blank lines / whitespace
        """
        t = text or ""
        t = re.sub(r"https?://\S+", "", t, flags=re.IGNORECASE)
        t = re.sub(r"<[^>]+>", " ", t)
        # Normalize newlines and whitespace
        t = t.replace("\r\n", "\n").replace("\r", "\n")
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    @staticmethod
    def _word_tokens(name: str) -> list[str]:
        raw = re.findall(r"[A-Za-z0-9]{2,}", (name or "").lower())
        return [t for t in raw if len(t) >= 3]

    @functools.lru_cache(maxsize=512)
    def _company_alias_tokens_cached(self, symbol: str) -> tuple[str, ...]:
        sym = (symbol or "").strip().upper()
        if not sym:
            return tuple()
        try:
            info = yf.Ticker(sym).info or {}
        except Exception:
            info = {}
        name = str(info.get("longName") or info.get("shortName") or "").strip()
        if not name:
            return tuple()
        toks: list[str] = []
        for t in self._word_tokens(name):
            if t in self._STOP_TOKENS:
                continue
            toks.append(t)
        seen: set[str] = set()
        out: list[str] = []
        for t in toks:
            if t in seen:
                continue
            seen.add(t)
            out.append(t)
        return tuple(out[:10])

    async def _company_alias_tokens(self, symbol: str) -> set[str]:
        sym = (symbol or "").strip().upper()
        if not sym:
            return set()
        try:
            toks = await asyncio.to_thread(self._company_alias_tokens_cached, sym)
        except Exception:
            toks = tuple()
        return set(toks) if toks else set()

    @staticmethod
    def _ticker_regex(symbol: str) -> re.Pattern[str]:
        sym = (symbol or "").strip().upper()
        return re.compile(rf"(?i)\b{re.escape(sym)}\b")

    @staticmethod
    def _cashtag_regex(symbol: str) -> re.Pattern[str]:
        sym = (symbol or "").strip().upper()
        return re.compile(rf"(?i)\${re.escape(sym)}\b")

    def _is_obviously_relevant(self, *, text: str, symbol: str, alias_tokens: set[str]) -> bool:
        t = self._strip_urls_and_html(text)
        if not t:
            return False
        sym = (symbol or "").strip().upper()
        if not sym:
            return False
        if self._cashtag_regex(sym).search(t):
            return True
        if self._ticker_regex(sym).search(t):
            return True
        low = t.lower()
        for tok in alias_tokens:
            if len(tok) < 4:
                continue
            if re.search(rf"(?i)\b{re.escape(tok)}\b", low):
                return True
        return False

    def _is_borderline_worth_llm(self, *, text: str) -> bool:
        t = self._strip_urls_and_html(text)
        if not t:
            return False
        if self._MACRO_RX.search(t) or self._HIGH_SIGNAL_RX.search(t):
            return True
        return False

    async def _llm_relevance_gate_batch(
        self,
        *,
        symbol: str,
        posts: list[RawContextItem],
        max_n: int,
    ) -> dict[int, dict[str, Any]]:
        if not self._settings.anthropic_api_key:
            return {}
        sym = (symbol or "").strip().upper()
        if not sym or not posts:
            return {}
        n = max(0, min(int(max_n), len(posts)))
        if n <= 0:
            return {}

        rows: list[dict[str, Any]] = []
        for i, it in enumerate(posts[:n]):
            txt = self._strip_urls_and_html(it.text or it.title or "")
            if not txt:
                continue
            rows.append(
                {
                    "idx": int(i),
                    "source": str(it.source or ""),
                    "text": txt[: int(self._SOCIAL_GATE_MAX_CHARS_PER_POST)],
                }
            )
        if not rows:
            return {}

        prompt = f"""You are filtering social posts for a market context feed.
Symbol: {sym}

Decide whether each post should be INCLUDED in the social analysis for {sym}.
Rules:
- Include if it clearly refers to {sym} (company or ticker), even implicitly.
- If it does NOT refer to {sym}, you may still include it ONLY if it is market-moving macro (Fed/CPI/rates/geopolitics) that is likely to affect equities broadly.
- Output ONLY valid JSON (no markdown) as a list of objects:
[{{"idx":0,"include":true|false,"is_macro_market_moving":true|false}}, ...]

Posts:
{json.dumps(rows, ensure_ascii=False)}
"""

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
                    "max_tokens": 700,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=90.0,
            )
            r.raise_for_status()
            payload = r.json()
            blocks = payload.get("content") or []
            raw = ""
            for b in blocks:
                if isinstance(b, dict) and b.get("type") == "text":
                    raw += str(b.get("text", ""))
            m = re.search(r"\[[\s\S]*\]", raw)
            if not m:
                return {}
            data = json.loads(m.group(0))
            if not isinstance(data, list):
                return {}
            out: dict[int, dict[str, Any]] = {}
            for row in data:
                if not isinstance(row, dict):
                    continue
                try:
                    idx = int(row.get("idx"))
                except Exception:
                    continue
                out[idx] = {
                    "include": bool(row.get("include")),
                    "is_macro_market_moving": bool(row.get("is_macro_market_moving")),
                }
            return out
        except Exception:
            return {}

    async def _tier1_official(self, symbol: str) -> list[RawContextItem]:
        sym = symbol.upper()
        out: list[RawContextItem] = []
        # SEC filings (official, no key)
        try:
            filings = await self._sec.recent_filings(sym, forms=["8-K", "10-Q", "10-K"], limit=8)
            for f in filings:
                title = f"{f.form} filed"
                if f.filed:
                    title = f"{f.form} filed ({f.filed.isoformat()})"
                out.append(
                    RawContextItem(
                        source="sec_edgar",
                        tier=1,
                        title=title,
                        text=f"{sym} {f.form} filing",
                        url=str(f.filing_url) if f.filing_url else None,
                        occurred_at=datetime.combine(f.filed, datetime.min.time(), tzinfo=timezone.utc)
                        if f.filed
                        else None,
                    )
                )
        except Exception:
            pass

        # FMP (official-ish / normalized)
        try:
            out.extend(await self._fmp.stock_news(sym, limit=12))
        except Exception:
            pass
        return out

    async def _tier2_news(self, symbol: str) -> list[RawContextItem]:
        sym = symbol.upper()
        items: list[RawContextItem] = []
        # Primary: NewsAPI (keyed)
        try:
            items = await self._newsapi.everything(sym, limit=20)
        except Exception:
            items = []
        if items:
            return items

        # Fallback: yfinance (no key)
        try:
            return await self._yfn.ticker_news(sym, limit=20)
        except Exception:
            return []

    async def _tier3_rumors(self, symbol: str) -> list[RawContextItem]:
        try:
            # Tier-3 = market-moving social sentiment (no keys). Fail-soft by design.
            n = int(self._SOCIAL_MAX_POSTS_PER_ACCOUNT)
            n = min(5, max(3, n))
            return await self._social.latest_posts(limit_per_account=n)
        except Exception:
            return []

    async def _gate_social_posts(
        self,
        *,
        symbol: str,
        posts: list[RawContextItem],
    ) -> tuple[list[RawContextItem], dict[str, int]]:
        """
        Smart relevance gating for social posts:
        - include obvious symbol/company mentions via cheap rules
        - for borderline posts, use a single batched LLM gate (if available)
        - allow macro market-moving posts even without symbol mention (policy)
        Always fail-soft: return a best-effort filtered list + stats.
        """
        sym = (symbol or "").strip().upper()
        if not sym or not posts:
            return [], {"total": int(len(posts or [])), "obvious": 0, "borderline": 0, "included": 0}

        alias_tokens = await self._company_alias_tokens(sym)
        obvious: list[RawContextItem] = []
        macro_direct: list[RawContextItem] = []
        borderline: list[RawContextItem] = []
        for it in posts:
            txt = it.text or it.title or ""
            # Always preserve internal diagnostic social messages so the UI can explain why empty.
            if str(it.source or "").strip().lower() == "social":
                obvious.append(it)
                continue
            if self._is_obviously_relevant(text=txt, symbol=sym, alias_tokens=alias_tokens):
                obvious.append(it)
            else:
                # Keep a small set of macro/high-signal items even if LLM gating is unavailable.
                # This prevents the social section from being empty for most symbols, because
                # many tracked accounts post market-wide headlines.
                t2 = self._strip_urls_and_html(txt)
                if t2 and (self._MACRO_RX.search(t2) or self._HIGH_SIGNAL_RX.search(t2)):
                    macro_direct.append(it)
                elif self._is_borderline_worth_llm(text=txt):
                    borderline.append(it)

        # Bound borderline list before gating to keep latency controlled.
        max_b = int(self._SOCIAL_GATE_MAX_BORDERLINE)
        max_b = max(0, min(max_b, len(borderline)))
        borderline = borderline[:max_b]
        max_m = int(self._SOCIAL_GATE_MAX_MACRO_DIRECT)
        max_m = max(0, min(max_m, len(macro_direct)))
        macro_direct = macro_direct[:max_m]

        # Default: only obvious. If LLM gate exists, it can add some borderlines.
        included = [*obvious, *macro_direct]
        if borderline:
            gate = await self._llm_relevance_gate_batch(symbol=sym, posts=borderline, max_n=len(borderline))
            # Gate indices correspond to borderline[:n] positions.
            for i, it in enumerate(borderline):
                g = gate.get(i) if isinstance(gate, dict) else None
                if not isinstance(g, dict):
                    continue
                if bool(g.get("include")) or bool(g.get("is_macro_market_moving")):
                    included.append(it)
        # Light dedup by (source,url,title) to avoid repeats.
        seen: set[tuple[str, str, str]] = set()
        out: list[RawContextItem] = []
        for it in included:
            key = (str(it.source or ""), str(it.url or ""), str(it.title or ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(it)

        stats = {
            "total": int(len(posts)),
            "obvious": int(len(obvious)),
            "macro_direct": int(len(macro_direct)),
            "borderline": int(len(borderline)),
            "included": int(len(out)),
        }
        return out, stats

    async def _social_ai_bottom_line(self, *, symbol: str, items: list[RawContextItem]) -> dict[str, Any] | None:
        """
        AI synthesis over Tier-3 social items.
        Uses the existing Anthropic pipeline style (same HTTP client + ANTHROPIC_API_KEY in Settings).
        Fail-soft: returns None on any failure.
        """
        if not self._settings.anthropic_api_key:
            return None
        sym = (symbol or "").strip().upper()
        if not sym or not items:
            return None

        # Aggregate texts (bounded) so LLM gets representative content, not a dump.
        parts: list[str] = []
        for it in items[:40]:
            txt = (it.text or it.title or "").strip()
            if not txt:
                continue
            src = (it.source or "").strip()
            cleaned = self._strip_urls_and_html(txt)
            if not cleaned:
                continue
            parts.append(f"[{src}] {cleaned[:600]}")
        blob = self._strip_urls_and_html("\n".join(parts))
        if not blob:
            return None

        # Hard truncation guardrail to avoid context-length errors.
        max_chars = int(self._SOCIAL_AI_MAX_CHARS)
        if max_chars > 0 and len(blob) > max_chars:
            blob = blob[:max_chars]

        prompt = f"""You are a market analyst. You are given recent social posts from influential accounts on X (Twitter) and Truth Social.
Your task: produce a short synthesis for the stock symbol {sym}.

Rules:
- Prefer posts that clearly refer to {sym} (company or ticker/cashtag).
- If there are NO clear {sym} mentions, you may still summarize the dominant MARKET-WIDE narrative (Fed/CPI/rates/geopolitics) and explicitly say there were no direct mentions of {sym}.
- Do NOT invent facts. Only use what is present in the posts.
- Output ONLY valid JSON (no markdown), exactly in this schema:
{{"bottom_line_he":"...","verdict":"bullish|bearish|mixed","primary_narrative_he":"..."}}

Guidance:
- bottom_line_he: 2-5 sentences in Hebrew. Insightful, decisive, and readable.
- primary_narrative_he: short Hebrew paragraph describing the primary narrative.
- verdict: bullish/bearish/mixed. If the content is mostly macro and not about {sym}, use "mixed".

Posts:
---
{blob}
---"""

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
                    "max_tokens": 900,
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
                return None
            data = json.loads(m.group(0))
            if not isinstance(data, dict):
                return None
            verdict = str(data.get("verdict") or "").strip().lower()
            if verdict not in ("bullish", "bearish", "mixed"):
                verdict = "mixed"
            bottom = str(data.get("bottom_line_he") or "").strip()
            primary = str(data.get("primary_narrative_he") or "").strip()
            if not bottom:
                return None
            return {"ai_bottom_line_he": bottom, "ai_verdict": verdict, "ai_primary_narrative_he": primary}
        except Exception:
            return None

    async def build_feed(self, symbol: str) -> MarketContextFeedDTO:
        sym = symbol.upper()

        sources_attempted: list[str] = []
        errors: list[dict[str, object]] = []

        async def _wrap(name: str, coro):
            sources_attempted.append(name)
            try:
                return await coro
            except Exception as exc:
                errors.append({"source": name, "error": f"{type(exc).__name__}: {exc}"})
                return []

        tier1_task = asyncio.create_task(_wrap("tier1_official", self._tier1_official(sym)))
        tier2_task = asyncio.create_task(_wrap("tier2_news", self._tier2_news(sym)))
        tier3_task = asyncio.create_task(_wrap("tier3_rumors", self._tier3_rumors(sym)))
        tier1, tier2, tier3 = await asyncio.gather(tier1_task, tier2_task, tier3_task)

        tier3_filtered: list[RawContextItem] = tier3
        social_stats: dict[str, int] | None = None
        try:
            tier3_filtered, social_stats = await self._gate_social_posts(symbol=sym, posts=tier3)
        except Exception:
            tier3_filtered, social_stats = tier3, None

        # AI synthesis for Tier-3 social (best-effort).
        social_ai = None
        try:
            social_ai = await self._social_ai_bottom_line(symbol=sym, items=tier3_filtered)
        except Exception:
            social_ai = None

        # IMPORTANT: apply gating before downstream NLP (FinBERT + categorization) to reduce noise.
        all_items = [*tier1, *tier2, *tier3_filtered]
        # Prepare sentiment inputs (FinBERT is heavier; keep it bounded).
        sentiment_texts: list[str] = []
        for it in all_items[:60]:
            sentiment_texts.append((it.text or it.title)[:900])

        sentiments = []
        try:
            sentiments = await self._finbert.score_sentences(sentiment_texts)
        except Exception:
            sentiments = []

        def _sent(idx: int):
            if 0 <= idx < len(sentiments):
                s = sentiments[idx]
                # pick best score for label
                lab = (s.label or "").lower()
                score = None
                if lab == "positive":
                    score = s.score_positive
                elif lab == "negative":
                    score = s.score_negative
                else:
                    score = s.score_neutral
                return lab, float(score) if score is not None else None
            return None, None

        buckets: dict[str, list[MarketContextItemDTO]] = {"news": [], "macro": [], "rumors": [], "corporate": []}
        for idx, it in enumerate(all_items[:60]):
            cat, tags = categorize_and_tag(it.text or it.title, source=it.source, tier=it.tier)
            rel = time_decay_relevance(it.occurred_at, half_life_hours=48.0)
            lab, score = _sent(idx)
            buckets[cat].append(
                MarketContextItemDTO(
                    id=it.stable_id(sym),
                    source=it.source,
                    tier=int(it.tier),
                    title=it.title,
                    url=it.url,
                    occurred_at=it.occurred_at,
                    summary=it.text[:600] if it.text else None,
                    tags=tags,
                    sentiment_label=lab,
                    sentiment_score=score,
                    relevance=rel,
                )
            )

        # Sort each section by relevance then recency.
        def _sort_key(x: MarketContextItemDTO):
            ts = x.occurred_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
            return (float(x.relevance or 0.0), ts)

        for k in buckets:
            buckets[k].sort(key=_sort_key, reverse=True)

        sections = [
            MarketContextSectionDTO(
                id="news",
                title_he="חדשות ודיווחים",
                subtitle_he="כותרות שיכולות להסביר תנועה/סנטימנט קצר טווח",
                items=buckets["news"],
            ),
            MarketContextSectionDTO(
                id="macro_speeches",
                title_he="מקרו (ריבית, אינפלציה, מדיניות)",
                subtitle_he="ידיעות כלל-שוק שיכולות להשפיע על מכפילים",
                items=buckets["macro"],
            ),
            MarketContextSectionDTO(
                id="rumors",
                title_he="סנטימנט רשת (X + Truth Social)",
                subtitle_he="לא מאומת — להשתמש בזהירות ולאמת מול מקור רשמי",
                ai_bottom_line_he=(social_ai or {}).get("ai_bottom_line_he") if isinstance(social_ai, dict) else None,
                ai_verdict=(social_ai or {}).get("ai_verdict") if isinstance(social_ai, dict) else None,
                ai_debug=social_stats if isinstance(social_stats, dict) else None,
                items=buckets["rumors"],
            ),
            MarketContextSectionDTO(
                id="corporate",
                title_he="אירועי חברה (דוחות/הנחיות/רגולציה)",
                subtitle_he="אירועים שעשויים לשנות את התזה או את פרמיית הסיכון",
                items=buckets["corporate"],
            ),
        ]

        return MarketContextFeedDTO(
            ok=True,
            symbol=sym,
            fetched_at_utc=datetime.now(tz=timezone.utc),
            as_of=datetime.now(tz=timezone.utc),
            message_he=None,
            sources_attempted=sources_attempted,
            errors=errors,
            sections=sections,
        )

