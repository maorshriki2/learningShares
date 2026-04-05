from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import yfinance as yf

from market_intel.modules.peers.peer_map import lookup_peers


@dataclass
class PeerMetrics:
    symbol: str
    name: str
    sector: str
    market_cap: float | None
    pe_ratio: float | None
    ev_ebitda: float | None
    operating_margin: float | None
    revenue_growth: float | None
    price: float | None
    is_subject: bool = False


def _fetch_one(symbol: str) -> dict[str, Any]:
    try:
        info = yf.Ticker(symbol).info or {}
        return info
    except Exception:
        return {}


def _metrics_from_info(symbol: str, info: dict[str, Any], is_subject: bool = False) -> PeerMetrics:
    def _f(key: str) -> float | None:
        v = info.get(key)
        return float(v) if v is not None else None

    return PeerMetrics(
        symbol=symbol.upper(),
        name=str(info.get("shortName") or info.get("longName") or symbol),
        sector=str(info.get("sector") or info.get("industry") or "Unknown"),
        market_cap=_f("marketCap"),
        pe_ratio=_f("trailingPE") or _f("forwardPE"),
        ev_ebitda=_f("enterpriseToEbitda"),
        operating_margin=_f("operatingMargins"),
        revenue_growth=_f("revenueGrowth"),
        price=_f("currentPrice") or _f("regularMarketPrice"),
        is_subject=is_subject,
    )


async def build_peer_table(
    symbol: str,
    extra_peers: list[str] | None = None,
) -> list[PeerMetrics]:
    sym = symbol.upper()
    subject_info = await asyncio.to_thread(_fetch_one, sym)
    industry = subject_info.get("sector") or subject_info.get("industry") or ""
    peers = lookup_peers(sym, str(industry))
    if extra_peers:
        for p in extra_peers:
            p = p.upper()
            if p not in peers and p != sym:
                peers.append(p)
    peers = peers[:6]
    all_syms = [sym] + peers

    def _batch() -> list[dict[str, Any]]:
        return [_fetch_one(s) for s in all_syms]

    infos = await asyncio.to_thread(_batch)
    rows: list[PeerMetrics] = []
    for s, info in zip(all_syms, infos, strict=False):
        rows.append(_metrics_from_info(s, info, is_subject=(s == sym)))
    return rows
