from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
import yfinance as yf

from market_intel.api.dependencies import StateDep, get_settings_dep
from market_intel.config.settings import Settings
from market_intel.infrastructure.market_data.instrument_info import SECTOR_MAP

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

# Fallback universe for daily watchlist when dynamic screeners are restricted.
# Keep this backend-local (don't import UI modules).
_SECTOR_UNIVERSE: dict[str, tuple[str, ...]] = {
    "Technology": (
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "META",
        "AVGO",
        "ORCL",
        "IBM",
        "CRM",
        "ADBE",
        "TSM",
        "NOW",
        "PANW",
        "CRWD",
        "AMD",
        "INTC",
        "OKTA",
        "PLTR",
        "DDOG",
        "NET",
        "SNOW",
    ),
    "Healthcare": (
        "UNH",
        "JNJ",
        "LLY",
        "PFE",
        "MRK",
        "ABBV",
        "TMO",
        "DHR",
        "ABT",
        "AMGN",
        "ISRG",
        "VRTX",
        "REGN",
        "GILD",
        "SYK",
        "MRNA",
        "DXCM",
    ),
    "Financial Services": (
        "JPM",
        "BAC",
        "WFC",
        "C",
        "GS",
        "MS",
        "SCHW",
        "BLK",
        "AXP",
        "V",
        "MA",
        "PYPL",
        "COF",
        "SOFI",
    ),
    "Consumer Cyclical": (
        "AMZN",
        "TSLA",
        "HD",
        "LOW",
        "NKE",
        "MCD",
        "SBUX",
        "BKNG",
        "ABNB",
        "DIS",
        "CMG",
        "ROST",
        "ETSY",
    ),
    "Industrials": (
        "GE",
        "CAT",
        "HON",
        "UPS",
        "DE",
        "BA",
        "RTX",
        "LMT",
        "NOC",
        "GD",
        "LHX",
    ),
}


def _utc_date_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _ttl_until_next_utc_day_seconds() -> int:
    now = datetime.now(timezone.utc)
    next_day = (now.date() + timedelta(days=1))
    next_midnight = datetime.combine(next_day, datetime.min.time(), tzinfo=timezone.utc)
    return max(int((next_midnight - now).total_seconds()), 60)


def _bucket_bounds(bucket: str) -> tuple[float | None, float | None]:
    """
    Market-cap buckets (USD):
    - Large: >= 10B
    - Mid:   2B .. <10B
    - Small: 300M .. <2B
    """
    b = (bucket or "").strip().lower()
    if b in {"large", "largecap", "large_cap", "large cap"}:
        return (10_000_000_000.0, None)
    if b in {"mid", "midcap", "mid_cap", "mid cap"}:
        return (2_000_000_000.0, 10_000_000_000.0)
    if b in {"small", "smallcap", "small_cap", "small cap"}:
        return (300_000_000.0, 2_000_000_000.0)
    raise ValueError("Unknown bucket")


def _finite_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _read_dotenv_value(*, key: str, dotenv_path: Path) -> str | None:
    """
    Minimal .env parser (KEY=VAL). Used as a fallback so editing `.env` works without restarting API.
    """
    try:
        raw = dotenv_path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() != key:
            continue
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        return v or None
    return None


def _bucket_name(market_cap: float | None) -> str | None:
    if market_cap is None or not math.isfinite(float(market_cap)):
        return None
    mc = float(market_cap)
    if mc >= 10_000_000_000:
        return "Large Cap"
    if mc >= 2_000_000_000:
        return "Mid Cap"
    if mc >= 300_000_000:
        return "Small Cap"
    return None


@router.get("/sector-buckets")
async def sector_buckets(
    *,
    sectors: list[str] = Query(default_factory=list),
    large_n: int = 5,
    mid_n: int = 5,
    small_n: int = 5,
    state: StateDep,
    settings: Settings = Depends(get_settings_dep),
) -> dict[str, object]:
    """
    Dynamic watchlist screener: returns Top-N tickers per sector per market-cap bucket.

    Primary provider: FMP company screener (requires FMP_API_KEY).
    """
    # --- Daily cache (one refresh per UTC day) ---
    date_key = _utc_date_key()
    payload_key = {
        "date_utc": date_key,
        "sectors": list(sectors or []),
        "large_n": int(large_n),
        "mid_n": int(mid_n),
        "small_n": int(small_n),
    }
    daily_cache_key = f"watchlist:sector-buckets:{json.dumps(payload_key, sort_keys=True, default=str)}"
    try:
        cached = await state.cache.get(daily_cache_key)
    except Exception:
        cached = None
    if cached:
        try:
            obj = json.loads(cached)
            if isinstance(obj, dict):
                obj.setdefault("cached_date_utc", date_key)
                obj.setdefault("cached", True)
                return obj  # type: ignore[return-value]
        except Exception:
            pass

    if not sectors:
        # sensible defaults (matches existing Sector enum naming, but using FMP sector strings)
        sectors = [
            "Technology",
            "Healthcare",
            "Financial Services",
            "Consumer Cyclical",
            "Consumer Defensive",
            "Industrials",
            "Energy",
            "Utilities",
            "Real Estate",
            "Basic Materials",
            "Communication Services",
        ]

    fmp_key = getattr(settings, "fmp_api_key", None)
    if not fmp_key:
        # Fallback: read `.env` directly so key changes are picked up without restart.
        fmp_key = _read_dotenv_value(key="FMP_API_KEY", dotenv_path=Path(".env"))

    # If FMP key is missing, we'll still fall back to yfinance universe below.

    base_url = "https://financialmodelingprep.com"
    endpoint_stable = "/stable/company-screener"
    endpoint_legacy = "/api/v3/stock-screener"

    async def _screen_sector(*, sector: str, limit: int = 200) -> tuple[list[dict[str, object]], dict[str, object]]:
        """
        One request per sector, then bucket locally (reduces API usage: 1×sector instead of 3×sector).
        """
        params: dict[str, object] = {
            "apikey": fmp_key,
            "sector": sector,
            "limit": int(max(20, min(250, limit))),
            "isActivelyTrading": "true",
        }

        async def _call(url: str) -> tuple[httpx.Response | None, dict[str, object] | None]:
            try:
                r0 = await state.http_client.get(url, params=params)
                r0.raise_for_status()
                return r0, None
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else None
                txt = exc.response.text[:500] if exc.response is not None else None
                return None, {"status_code": status, "body": txt}
            except Exception as exc:
                return None, {"error": str(exc)}

        # Try stable first; some plans restrict it (402). Fallback to legacy v3.
        r, err = await _call(f"{base_url}{endpoint_stable}")
        used = "fmp.stable.company-screener"
        if r is None:
            status = err.get("status_code") if isinstance(err, dict) else None  # type: ignore[union-attr]
            if status in (401, 402, 403, 404):
                r, err2 = await _call(f"{base_url}{endpoint_legacy}")
                if r is not None:
                    used = "fmp.api.v3.stock-screener"
                else:
                    return [], {"ok": False, "provider": used, **(err or {}), "fallback": err2}
            else:
                return [], {"ok": False, "provider": used, **(err or {})}

        items = r.json()
        if not isinstance(items, list):
            return [], {"ok": False, "provider": used, "error": "unexpected_payload"}

        rows: list[dict[str, object]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            sym = (it.get("symbol") or "").strip().upper()
            if not sym:
                continue
            mc = _finite_float(it.get("marketCap"))
            b = _bucket_name(mc)
            rows.append(
                {
                    "sector": sector,
                    "bucket": b,
                    "symbol": sym,
                    "name": it.get("companyName") or it.get("name"),
                    "market_cap": mc,
                    "price": _finite_float(it.get("price")),
                    "beta": _finite_float(it.get("beta")),
                    "exchange": it.get("exchange"),
                    "country": it.get("country"),
                    "source": "fmp.company-screener",
                }
            )
        # sort by market cap desc for stable top-N selection
        rows.sort(key=lambda x: float(x.get("market_cap") or 0.0), reverse=True)
        return rows, {"ok": True, "provider": used, "n_returned": len(rows)}

    out: dict[str, object] = {"ok": True, "message": "", "sectors": sectors, "buckets": {}}
    buckets: dict[str, dict[str, list[dict[str, object]]]] = {}
    provider_notes: dict[str, object] = {}
    any_provider_ok = False
    any_items = False

    # --- Provider 1: FMP (preferred) ---
    if fmp_key:
        for sector in sectors:
            sec = str(sector).strip()
            if not sec:
                continue
            rows, note = await _screen_sector(sector=sec, limit=220)
            provider_notes[sec] = note
            if isinstance(note, dict) and note.get("ok") is True:
                any_provider_ok = True
            large = [r for r in rows if r.get("bucket") == "Large Cap"][:large_n]
            mid = [r for r in rows if r.get("bucket") == "Mid Cap"][:mid_n]
            small = [r for r in rows if r.get("bucket") == "Small Cap"][:small_n]
            if large or mid or small:
                any_items = True
            buckets[sec] = {"Large Cap": large, "Mid Cap": mid, "Small Cap": small}
    else:
        provider_notes["fmp"] = {"ok": False, "error": "missing_api_key"}

    # --- Provider 2: fallback universe + yfinance ---
    if not any_items:
        out["message"] = "FMP unavailable/restricted → fallback universe (yfinance)."
        provider_notes["fallback"] = {"ok": True, "provider": "yfinance.universe"}

        sem = asyncio.Semaphore(10)

        async def _yf_info(sym: str, *, sector_label: str) -> dict[str, object] | None:
            s = (sym or "").strip().upper()
            if not s:
                return None

            def _sync() -> dict[str, Any]:
                t = yf.Ticker(s)
                return t.info or {}

            async with sem:
                try:
                    info = await asyncio.to_thread(_sync)
                except Exception:
                    return None

            name = info.get("longName") or info.get("shortName")
            market_cap = _finite_float(info.get("marketCap"))
            price = _finite_float(
                info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
            )
            beta = _finite_float(info.get("beta"))

            # Normalize sector using the shared SECTOR_MAP when possible
            sector_raw = info.get("sector") or info.get("industry")
            sector_norm = None
            if sector_raw is not None:
                mapped = SECTOR_MAP.get(str(sector_raw))
                sector_norm = str(mapped) if mapped is not None else str(sector_raw)

            b = _bucket_name(market_cap)
            return {
                "sector": sector_label,
                "bucket": b,
                "symbol": s,
                "name": str(name) if name is not None else None,
                "market_cap": market_cap,
                "price": price,
                "beta": beta,
                "source": "yfinance.universe",
            }

        for sector in sectors:
            sec = str(sector).strip()
            if not sec:
                continue
            tickers = _SECTOR_UNIVERSE.get(sec, ())
            infos = await asyncio.gather(*[_yf_info(t, sector_label=sec) for t in tickers])
            rows = [r for r in infos if isinstance(r, dict) and r.get("market_cap") is not None]
            rows.sort(key=lambda x: float(x.get("market_cap") or 0.0), reverse=True)
            large = [r for r in rows if r.get("bucket") == "Large Cap"][:large_n]
            mid = [r for r in rows if r.get("bucket") == "Mid Cap"][:mid_n]
            small = [r for r in rows if r.get("bucket") == "Small Cap"][:small_n]
            if large or mid or small:
                any_items = True
            buckets[sec] = {"Large Cap": large, "Mid Cap": mid, "Small Cap": small}

    out["buckets"] = buckets
    if not any_items:
        out["ok"] = False
        out["message"] = (
            "No items available from providers (FMP restricted/unavailable; fallback empty)."
        )
    out["explain"] = {
        "provider_order": ["fmp", "yfinance_universe"],
        "bucket_thresholds_usd": {
            "Large Cap": {"min": 10_000_000_000, "max": None},
            "Mid Cap": {"min": 2_000_000_000, "max": 10_000_000_000},
            "Small Cap": {"min": 300_000_000, "max": 2_000_000_000},
        },
        "fmp_endpoints": {
            "stable": f"{base_url}{endpoint_stable}",
            "legacy_v3": f"{base_url}{endpoint_legacy}",
        },
        "provider_notes": provider_notes,
        "rate_limit_hint": "This endpoint is optimized to 1 request per sector per refresh. Add caching for stricter quotas.",
    }
    # Store daily cache (so UI refreshes won't recompute within same UTC day)
    try:
        ttl = _ttl_until_next_utc_day_seconds()
        await state.cache.set(daily_cache_key, json.dumps(out, ensure_ascii=False, default=str), ttl_seconds=ttl)
    except Exception:
        pass
    return out

