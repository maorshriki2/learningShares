from __future__ import annotations

import math
import statistics
from typing import Any

from fastapi import APIRouter

from market_intel.modules.peers.peer_analysis import PeerMetrics, build_peer_table

router = APIRouter(prefix="/peers", tags=["peers"])


def _row(m: PeerMetrics) -> dict[str, Any]:
    def _fmt(v: float | None) -> float | None:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return round(float(v), 4)

    return {
        "symbol": m.symbol,
        "name": m.name,
        "sector": m.sector,
        "market_cap": _fmt(m.market_cap),
        "pe_ratio": _fmt(m.pe_ratio),
        "ev_ebitda": _fmt(m.ev_ebitda),
        "operating_margin": _fmt(m.operating_margin),
        "revenue_growth": _fmt(m.revenue_growth),
        "price": _fmt(m.price),
        "is_subject": m.is_subject,
    }


@router.get("/{symbol}")
async def peer_comparison(
    symbol: str,
    extra: str = "",
) -> dict[str, object]:
    extras = [x.strip().upper() for x in extra.split(",") if x.strip()] if extra else []
    rows = await build_peer_table(symbol.upper(), extra_peers=extras)
    data = [_row(r) for r in rows]

    def _attach_zscores(rows_data: list[dict[str, Any]], key: str, out_key: str) -> None:
        vals = [float(r[key]) for r in rows_data if r.get(key) is not None]
        if len(vals) < 2:
            return
        mu = statistics.mean(vals)
        sd = statistics.stdev(vals)
        if sd < 1e-9:
            return
        for r in rows_data:
            v = r.get(key)
            if v is not None:
                r[out_key] = round((float(v) - mu) / sd, 3)

    _attach_zscores(data, "pe_ratio", "z_pe_ratio")
    _attach_zscores(data, "ev_ebitda", "z_ev_ebitda")

    def _avg(key: str) -> float | None:
        vals = [r[key] for r in data if r[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    sector_avg = {
        "symbol": "Sector Avg",
        "name": "—",
        "sector": "—",
        "market_cap": _avg("market_cap"),
        "pe_ratio": _avg("pe_ratio"),
        "ev_ebitda": _avg("ev_ebitda"),
        "operating_margin": _avg("operating_margin"),
        "revenue_growth": _avg("revenue_growth"),
        "price": None,
        "is_subject": False,
    }
    return {"rows": data, "sector_avg": sector_avg}
