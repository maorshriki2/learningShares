from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from market_intel.config.settings import Settings
from market_intel.infrastructure.cache.redis_cache import MemoryCache, RedisCache, cache_key
from market_intel.infrastructure.market_context.providers import RawContextItem


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _clean_text(s: str) -> str:
    # Keep it simple and robust (no heavy normalization).
    s = (s or "").replace("\u00a0", " ").strip()
    # Collapse whitespace
    return " ".join(s.split())


@dataclass(frozen=True)
class SocialPost:
    platform: str
    handle: str
    text: str
    url: str | None
    occurred_at: datetime | None

    def to_raw_item(self) -> RawContextItem:
        title = f"{self.platform}: @{self.handle}"
        return RawContextItem(
            source=self.platform,
            tier=3,
            title=title,
            text=self.text or title,
            url=self.url,
            occurred_at=self.occurred_at,
        )


class XNitterScraper:
    """
    Fetch recent posts for specific X (Twitter) accounts using Nitter via `ntscraper`.
    - No API keys.
    - Fail-soft: any error => [].
    """

    def __init__(
        self,
        *,
        settings: Settings,
        cache: MemoryCache | RedisCache,
        nitter_instances: list[str] | None = None,
    ) -> None:
        self._settings = settings
        self._cache = cache
        self._instances = nitter_instances or [
            # Public instances change often; rotate and fail-soft.
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.fdn.fr",
            "https://nitter.poast.org",
        ]

    async def latest_from_handles(
        self,
        handles: list[str],
        *,
        limit_per_handle: int = 5,
        cache_ttl_seconds: int | None = None,
    ) -> list[SocialPost]:
        # Preferred path: Nitter via `ntscraper` (no auth). Public instances are unreliable;
        # if they are down, we fail-soft and let the UI show a diagnostic item.
        try:
            from ntscraper import Nitter  # type: ignore[import-not-found]
        except Exception:
            Nitter = None  # type: ignore[assignment]

        ttl = int(cache_ttl_seconds or max(60, int(self._settings.cache_ttl_seconds)))
        out: list[SocialPost] = []

        # `ntscraper` is sync + can block; run in a thread.
        async def _one(handle: str) -> list[SocialPost]:
            h = (handle or "").strip().lstrip("@")
            if not h:
                return []
            ck = cache_key("social:x:nitter:user", {"u": h.lower(), "n": int(limit_per_handle)})
            cached = await self._cache.get(ck)
            if cached:
                try:
                    if isinstance(cached, bytes):
                        cached = cached.decode("utf-8", errors="ignore")
                    data = json.loads(str(cached))
                    if isinstance(data, list):
                        posts: list[SocialPost] = []
                        for row in data:
                            if not isinstance(row, dict):
                                continue
                            posts.append(
                                SocialPost(
                                    platform="x",
                                    handle=h,
                                    text=str(row.get("text") or ""),
                                    url=str(row.get("url") or "") or None,
                                    occurred_at=_parse_dt(row.get("occurred_at")),
                                )
                            )
                        return posts
                except Exception:
                    pass

            def _load_sync_nitter() -> list[dict[str, Any]]:
                if Nitter is None:
                    return []
                # Rotate instances: the library accepts `instances` list.
                scraper = Nitter(instances=self._instances)
                # Return shape varies by version; treat as untrusted.
                res = scraper.get_tweets(h, mode="user", number=int(limit_per_handle))
                if isinstance(res, dict):
                    tweets = res.get("tweets") or res.get("data") or res.get("items") or []
                    return tweets if isinstance(tweets, list) else []
                if isinstance(res, list):
                    return res
                return []

            try:
                rows = await asyncio.to_thread(_load_sync_nitter)
            except Exception:
                return []

            posts_out: list[SocialPost] = []
            for row in rows[: int(limit_per_handle)]:
                if not isinstance(row, dict):
                    continue
                text = _clean_text(str(row.get("text") or row.get("content") or ""))
                if not text:
                    continue
                link = str(row.get("link") or row.get("url") or "").strip() or None
                # Some versions provide `date` string; others `timestamp` epoch.
                dt = _parse_dt(row.get("date") or row.get("created_at") or row.get("timestamp"))
                posts_out.append(
                    SocialPost(platform="x", handle=h, text=text, url=link, occurred_at=dt)
                )

            try:
                await self._cache.set(
                    ck,
                    json.dumps(
                        [
                            {
                                "text": p.text,
                                "url": p.url,
                                "occurred_at": p.occurred_at.isoformat() if p.occurred_at else None,
                            }
                            for p in posts_out
                        ],
                        default=str,
                    ),
                    ttl_seconds=ttl,
                )
            except Exception:
                pass
            return posts_out

        # Small concurrency to reduce blocking, still fail-soft.
        tasks = [_one(h) for h in handles]
        try:
            all_lists = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            return []
        for item in all_lists:
            if isinstance(item, Exception):
                continue
            out.extend(item)
        return out


class TruthSocialHtmlScraper:
    """
    Best-effort Truth Social scraper via public HTML pages (no keys).
    - It may be blocked; fail-soft => [].
    - Parsing is heuristic and may degrade; still safe.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache

    def _headers(self) -> dict[str, str]:
        ua = (self._settings.sec_user_agent or "").strip() or "MarketIntelBot/1.0"
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    async def latest_from_handles(
        self,
        handles: list[str],
        *,
        limit_per_handle: int = 5,
        cache_ttl_seconds: int | None = None,
    ) -> list[SocialPost]:
        try:
            from bs4 import BeautifulSoup  # type: ignore[import-not-found]
        except Exception:
            return []

        ttl = int(cache_ttl_seconds or max(60, int(self._settings.cache_ttl_seconds)))
        out: list[SocialPost] = []

        async def _one(handle: str) -> list[SocialPost]:
            h = (handle or "").strip().lstrip("@")
            if not h:
                return []
            ck = cache_key("social:truth:html:user", {"u": h.lower(), "n": int(limit_per_handle)})
            cached = await self._cache.get(ck)
            if cached:
                try:
                    if isinstance(cached, bytes):
                        cached = cached.decode("utf-8", errors="ignore")
                    data = json.loads(str(cached))
                    if isinstance(data, list):
                        posts: list[SocialPost] = []
                        for row in data:
                            if not isinstance(row, dict):
                                continue
                            posts.append(
                                SocialPost(
                                    platform="truthsocial",
                                    handle=h,
                                    text=str(row.get("text") or ""),
                                    url=str(row.get("url") or "") or None,
                                    occurred_at=_parse_dt(row.get("occurred_at")),
                                )
                            )
                        return posts
                except Exception:
                    pass

            url = f"https://truthsocial.com/@{h}"
            try:
                r = await self._client.get(
                    url,
                    headers=self._headers(),
                    timeout=self._settings.http_timeout_seconds,
                    follow_redirects=True,
                )
                if r.status_code in (401, 403, 429) or r.status_code >= 500:
                    return []
                r.raise_for_status()
                html = r.text
            except Exception:
                return []

            soup = BeautifulSoup(html, "lxml")

            posts_out: list[SocialPost] = []

            # Heuristic parsing:
            # - Try `article` blocks (common for social feeds)
            # - Fallback: look for divs with "status" in class names
            blocks = soup.select("article") or soup.select("div[class*='status']")
            for blk in blocks:
                if len(posts_out) >= int(limit_per_handle):
                    break
                txt = ""
                # Prefer visible content nodes.
                cand = blk.select_one("div[class*='status__content']") or blk.select_one(
                    "div[class*='content']"
                )
                if cand is not None:
                    txt = cand.get_text(" ", strip=True)
                else:
                    txt = blk.get_text(" ", strip=True)
                text = _clean_text(txt)
                if not text or len(text) < 5:
                    continue

                # Try to extract a permalink. If not found, keep profile URL.
                link = None
                a = blk.select_one("a[href*='/@']")
                if a and a.get("href"):
                    href = str(a.get("href"))
                    if href.startswith("/"):
                        link = f"https://truthsocial.com{href}"
                    elif href.startswith("http"):
                        link = href

                # Try to find time tag.
                dt = None
                t = blk.select_one("time")
                if t:
                    dt = _parse_dt(t.get("datetime") or t.get_text(strip=True))

                posts_out.append(
                    SocialPost(platform="truthsocial", handle=h, text=text, url=link or url, occurred_at=dt)
                )

            try:
                await self._cache.set(
                    ck,
                    json.dumps(
                        [
                            {
                                "text": p.text,
                                "url": p.url,
                                "occurred_at": p.occurred_at.isoformat() if p.occurred_at else None,
                            }
                            for p in posts_out
                        ],
                        default=str,
                    ),
                    ttl_seconds=ttl,
                )
            except Exception:
                pass

            return posts_out

        tasks = [_one(h) for h in handles]
        try:
            all_lists = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            return []
        for item in all_lists:
            if isinstance(item, Exception):
                continue
            out.extend(item)
        return out


class Tier3SocialSentimentProvider:
    """
    Tier-3 social sources aggregator (X + Truth Social).
    Always fail-soft: provider errors must never crash the app.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
        nitter_instances: list[str] | None = None,
    ) -> None:
        self._settings = settings
        self._x = XNitterScraper(settings=settings, cache=cache, nitter_instances=nitter_instances)
        self._truth = TruthSocialHtmlScraper(settings=settings, client=client, cache=cache)

        self._x_handles: list[str] = [
            "unusual_whales",
            "zerohedge",
            "DeItaone",
            "KobeissiLetter",
            "NickTimiraos",
            "LizAnnSonders",
            "charliebilello",
            "ripster47",
            "Prof_heist",
            "WOLF_Financial",
            "Mr_Derivatives",
            "StockMKTNewz",
            "elonmusk",
            "saylor",
            "sama",
        ]
        self._truth_handles: list[str] = [
            "realDonaldTrump",
            "DOGE",
            "DevinNunes",
            "EricTrump",
        ]

    async def latest_posts(self, *, limit_per_account: int = 4) -> list[RawContextItem]:
        try:
            x_task = asyncio.create_task(
                self._x.latest_from_handles(self._x_handles, limit_per_handle=int(limit_per_account))
            )
            truth_task = asyncio.create_task(
                self._truth.latest_from_handles(self._truth_handles, limit_per_handle=int(limit_per_account))
            )
            x_posts, truth_posts = await asyncio.gather(x_task, truth_task)
        except Exception:
            return []

        # If everything is blocked, return a single diagnostic item so the UI doesn't look broken.
        if not x_posts and not truth_posts:
            now = datetime.now(tz=timezone.utc)
            msg = (
                "Social sources were blocked/unavailable (X via Nitter returned no working instances; "
                "Truth Social returned 403). This is expected on some networks.\n\n"
                "Fix options:\n"
                "- Use a VPN / different network\n"
                "- Self-host a Nitter-compatible instance and configure it\n"
                "- Switch to an authenticated X data source (official API or paid scraping provider)"
            )
            return [
                RawContextItem(
                    source="social",
                    tier=3,
                    title="Social feed unavailable",
                    text=msg,
                    url=None,
                    occurred_at=now,
                )
            ]

        # De-dup lightly across platforms by hashing platform+handle+text prefix.
        seen: set[str] = set()
        items: list[RawContextItem] = []
        for p in [*x_posts, *truth_posts]:
            key = hashlib.sha1(
                f"{p.platform}|{p.handle}|{(p.text or '')[:140]}".encode("utf-8", errors="ignore")
            ).hexdigest()[:16]
            if key in seen:
                continue
            seen.add(key)
            items.append(p.to_raw_item())
        return items

