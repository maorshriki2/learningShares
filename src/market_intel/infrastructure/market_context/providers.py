from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import yfinance as yf

from market_intel.config.settings import Settings
from market_intel.infrastructure.cache.redis_cache import MemoryCache, RedisCache, cache_key


@dataclass(frozen=True)
class RawContextItem:
    source: str
    tier: int
    title: str
    text: str
    url: str | None
    occurred_at: datetime | None

    def stable_id(self, symbol: str) -> str:
        h = hashlib.sha1()
        h.update(symbol.upper().encode("utf-8"))
        h.update(b"|")
        h.update(self.source.encode("utf-8"))
        h.update(b"|")
        h.update((self.url or "").encode("utf-8"))
        h.update(b"|")
        h.update(self.title.encode("utf-8", errors="ignore"))
        return h.hexdigest()[:20]


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        # epoch seconds
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # ISO-ish
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


class FmpProvider:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache

    async def stock_news(self, symbol: str, limit: int = 25) -> list[RawContextItem]:
        if not self._settings.fmp_api_key:
            return []
        sym = symbol.upper()
        ck = cache_key("fmp:stock_news", {"s": sym, "n": int(limit)})
        cached = await self._cache.get(ck)
        if cached:
            try:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8", errors="ignore")
                data = json.loads(str(cached))
                if isinstance(data, list):
                    out: list[RawContextItem] = []
                    for row in data:
                        if not isinstance(row, dict):
                            continue
                        try:
                            row2 = dict(row)
                            row2["occurred_at"] = _parse_dt(row2.get("occurred_at"))
                            out.append(RawContextItem(**row2))
                        except Exception:
                            continue
                    return out
            except Exception:
                pass

        url = "https://financialmodelingprep.com/api/v3/stock_news"
        params = {"tickers": sym, "limit": int(limit), "apikey": self._settings.fmp_api_key}
        try:
            r = await self._client.get(url, params=params, timeout=self._settings.http_timeout_seconds)
            if r.status_code in (401, 403, 429) or r.status_code >= 500:
                return []
            r.raise_for_status()
            payload: Any = r.json()
        except Exception:
            return []

        out: list[RawContextItem] = []
        if isinstance(payload, list):
            for row in payload[:limit]:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                txt = str(row.get("text") or row.get("content") or "").strip()
                link = str(row.get("url") or row.get("link") or "").strip() or None
                dt = _parse_dt(row.get("publishedDate") or row.get("published_date"))
                if title:
                    out.append(
                        RawContextItem(
                            source="fmp",
                            tier=1,
                            title=title,
                            text=txt or title,
                            url=link,
                            occurred_at=dt,
                        )
                    )
        await self._cache.set(
            ck,
            json.dumps([x.__dict__ for x in out], default=str),
            ttl_seconds=max(60, int(self._settings.cache_ttl_seconds)),
        )
        return out


class NewsApiProvider:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache

    async def everything(self, symbol: str, limit: int = 25) -> list[RawContextItem]:
        if not self._settings.newsapi_key:
            return []
        sym = symbol.upper()
        ck = cache_key("newsapi:everything", {"s": sym, "n": int(limit)})
        cached = await self._cache.get(ck)
        if cached:
            try:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8", errors="ignore")
                data = json.loads(str(cached))
                if isinstance(data, list):
                    out: list[RawContextItem] = []
                    for row in data:
                        if not isinstance(row, dict):
                            continue
                        try:
                            row2 = dict(row)
                            row2["occurred_at"] = _parse_dt(row2.get("occurred_at"))
                            out.append(RawContextItem(**row2))
                        except Exception:
                            continue
                    return out
            except Exception:
                pass

        url = "https://newsapi.org/v2/everything"
        # Keep query simple and cheap; NewsAPI handles relevance/recency sorting.
        q = f'"{sym}" OR ${sym}'
        params = {
            "q": q,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": int(min(100, max(1, limit))),
            "apiKey": self._settings.newsapi_key,
        }
        try:
            r = await self._client.get(url, params=params, timeout=self._settings.http_timeout_seconds)
            if r.status_code in (401, 403, 429) or r.status_code >= 500:
                return []
            r.raise_for_status()
            payload: Any = r.json()
        except Exception:
            return []

        articles = payload.get("articles") if isinstance(payload, dict) else None
        out: list[RawContextItem] = []
        if isinstance(articles, list):
            for row in articles[:limit]:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                desc = str(row.get("description") or "").strip()
                content = str(row.get("content") or "").strip()
                link = str(row.get("url") or "").strip() or None
                dt = _parse_dt(row.get("publishedAt"))
                text = " ".join([x for x in (title, desc, content) if x]).strip()
                if title:
                    out.append(
                        RawContextItem(
                            source="newsapi",
                            tier=2,
                            title=title,
                            text=text or title,
                            url=link,
                            occurred_at=dt,
                        )
                    )

        await self._cache.set(
            ck,
            json.dumps([x.__dict__ for x in out], default=str),
            ttl_seconds=max(60, int(self._settings.cache_ttl_seconds)),
        )
        return out


class RedditJsonProvider:
    """
    Public Reddit JSON endpoints (no OAuth).
    NOTE: These endpoints can return 429/403; always fail-soft (return []).
    """

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache

    def _headers(self) -> dict[str, str]:
        # Reddit expects a descriptive User-Agent; reuse SEC identity by default.
        ua = (self._settings.sec_user_agent or "").strip() or "MarketIntelBot/1.0"
        return {"User-Agent": ua, "Accept": "application/json"}

    async def wsb_search(self, symbol: str, limit: int = 25) -> list[RawContextItem]:
        sym = symbol.upper()
        ck = cache_key("redditjson:wsb_search", {"s": sym, "n": int(limit)})
        cached = await self._cache.get(ck)
        if cached:
            try:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8", errors="ignore")
                data = json.loads(str(cached))
                if isinstance(data, list):
                    out: list[RawContextItem] = []
                    for row in data:
                        if not isinstance(row, dict):
                            continue
                        try:
                            row2 = dict(row)
                            row2["occurred_at"] = _parse_dt(row2.get("occurred_at"))
                            out.append(RawContextItem(**row2))
                        except Exception:
                            continue
                    return out
            except Exception:
                pass

        url = "https://www.reddit.com/r/wallstreetbets/search.json"
        # Use both plain ticker and $TICKER for retail posts.
        q = f'({sym} OR ${sym})'
        params = {
            "q": q,
            "restrict_sr": 1,
            "sort": "new",
            "t": "week",
            "limit": int(min(100, max(1, limit))),
        }
        try:
            r = await self._client.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self._settings.http_timeout_seconds,
            )
            if r.status_code in (401, 403, 429) or r.status_code >= 500:
                return []
            r.raise_for_status()
            payload: Any = r.json()
        except Exception:
            return []

        out: list[RawContextItem] = []
        data = payload.get("data") if isinstance(payload, dict) else None
        children = data.get("children") if isinstance(data, dict) else None
        if isinstance(children, list):
            for ch in children[:limit]:
                if not isinstance(ch, dict):
                    continue
                row = ch.get("data")
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                selftext = str(row.get("selftext") or "").strip()
                permalink = str(row.get("permalink") or "").strip()
                link = f"https://www.reddit.com{permalink}" if permalink else None
                dt = _parse_dt(row.get("created_utc"))
                txt = " ".join([x for x in (title, selftext) if x]).strip()
                if title:
                    out.append(
                        RawContextItem(
                            source="reddit_json",
                            tier=3,
                            title=title,
                            text=txt or title,
                            url=link,
                            occurred_at=dt,
                        )
                    )

        await self._cache.set(
            ck,
            json.dumps([x.__dict__ for x in out], default=str),
            ttl_seconds=max(60, int(self._settings.cache_ttl_seconds)),
        )
        return out


class YFinanceNewsProvider:
    def __init__(self) -> None:
        pass

    async def ticker_news(self, symbol: str, limit: int = 25) -> list[RawContextItem]:
        sym = symbol.upper()

        def _load() -> list[dict[str, Any]]:
            try:
                t = yf.Ticker(sym)
                rows = t.news or []
                return rows if isinstance(rows, list) else []
            except Exception:
                return []

        rows = await __import__("asyncio").to_thread(_load)
        out: list[RawContextItem] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            link = str(row.get("link") or row.get("url") or "").strip() or None
            dt = _parse_dt(row.get("providerPublishTime"))
            if title:
                out.append(
                    RawContextItem(
                        source="yfinance",
                        tier=2,
                        title=title,
                        text=title,
                        url=link,
                        occurred_at=dt,
                    )
                )
        return out

