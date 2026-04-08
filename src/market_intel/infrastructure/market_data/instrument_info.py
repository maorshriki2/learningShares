from __future__ import annotations

import asyncio
from typing import Any

import yfinance as yf

from market_intel.domain.entities.executive import ExecutiveProfile
from market_intel.domain.entities.instrument import Instrument
from market_intel.domain.value_objects.sector import Sector
from market_intel.domain.value_objects.symbol import Symbol

SECTOR_MAP: dict[str, Sector] = {
    "Technology": Sector.TECHNOLOGY,
    "Healthcare": Sector.HEALTHCARE,
    "Financial Services": Sector.FINANCIALS,
    "Financials": Sector.FINANCIALS,
    "Consumer Cyclical": Sector.CONSUMER_CYCLICAL,
    "Consumer Defensive": Sector.CONSUMER_DEFENSIVE,
    "Industrials": Sector.INDUSTRIALS,
    "Energy": Sector.ENERGY,
    "Utilities": Sector.UTILITIES,
    "Real Estate": Sector.REAL_ESTATE,
    "Basic Materials": Sector.MATERIALS,
    "Communication Services": Sector.COMMUNICATION,
}


async def load_instrument_profile(symbol: str) -> Instrument:
    def _sync() -> dict[str, Any]:
        t = yf.Ticker(symbol)
        info = t.info or {}
        return info

    info = await asyncio.to_thread(_sync)
    sec_raw = info.get("sector") or info.get("industry") or ""
    sector = SECTOR_MAP.get(str(sec_raw), Sector.UNKNOWN)
    beta = info.get("beta")
    name = info.get("longName") or info.get("shortName") or symbol
    exch = info.get("exchange") or ""
    return Instrument(
        symbol=Symbol(ticker=symbol),
        name=str(name),
        exchange=str(exch),
        sector=sector,
        beta=float(beta) if beta is not None else None,
    )


async def executives_from_yfinance(symbol: str) -> list[ExecutiveProfile]:
    def _sync() -> list[ExecutiveProfile]:
        t = yf.Ticker(symbol)
        rows = t.info.get("companyOfficers") or []
        out: list[ExecutiveProfile] = []
        for r in rows:
            name = r.get("name")
            title = r.get("title")
            if not name or not title:
                continue
            pay = r.get("totalPay")
            out.append(
                ExecutiveProfile(
                    symbol=symbol.upper(),
                    name=str(name),
                    title=str(title),
                    total_comp_usd=float(pay) if pay is not None else None,
                )
            )
        return out

    return await asyncio.to_thread(_sync)


async def last_price_and_shares(symbol: str) -> tuple[float | None, float | None]:
    def _sync() -> tuple[float | None, float | None]:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        info = t.info or {}
        px = fi.get("last_price") or fi.get("regular_market_price")
        if px is None:
            px = (
                info.get("regularMarketPrice")
                or info.get("currentPrice")
                or info.get("previousClose")
            )
        sh = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
        return (float(px) if px is not None else None, float(sh) if sh is not None else None)

    return await asyncio.to_thread(_sync)
