from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import asyncio
from fastapi import APIRouter, Depends, Query

from market_intel.api.dependencies import (
    get_fundamentals_service,
    get_governance_service,
    get_market_context_service,
    get_market_service,
)
from market_intel.application.services.fundamentals_service import FundamentalsService
from market_intel.application.services.governance_service import GovernanceService
from market_intel.application.services.market_context_service import MarketContextService
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.api.routers.instruments import instrument_summary
from market_intel.api.routers.peers import peer_comparison
from market_intel.api.routers.valuation import valuation_verdict
from market_intel.api.routers.market_rest import ohlcv as market_ohlcv
from market_intel.api.routers.market_rest import market_context_feed as market_context_feed_route
from market_intel.api.routers.market_rest import chart_technical_verdict as chart_technical_verdict_route
from market_intel.api.routers.macro import current_rates
from market_intel.modules.analytics.market_context_verdict import build_market_context_verdict
from market_intel.modules.analytics.stock360_composer import compose_stock360

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{symbol}/artifact")
async def analysis_artifact(
    symbol: str,
    include_explain: bool = True,
    timeframe: Timeframe = Timeframe.D1,
    limit: int = 320,
    years: int = 10,
    gov_year: int = 2024,
    gov_quarter: int = 4,
    peers_extra: str = "",
    mos_required: float = Query(default=0.15, ge=0.0, le=0.6),
    premium_threshold: float = Query(default=0.15, ge=0.0, le=1.0),
    wacc_span: float = Query(default=0.02, ge=0.0, le=0.2),
    terminal_span: float = Query(default=0.01, ge=0.0, le=0.1),
    grid_size: int = Query(default=5, ge=3, le=9),
    market: MarketDataService = Depends(get_market_service),
    fundamentals: FundamentalsService = Depends(get_fundamentals_service),
    governance: GovernanceService = Depends(get_governance_service),
    market_context: MarketContextService = Depends(get_market_context_service),
) -> dict[str, Any]:
    """
    Unified analysis artifact builder (v1).
    Fetches raw inputs once and produces:
    - valuation verdict
    - chart technical verdict
    - market context verdict (fail-soft)
    - composed Stock360 + trace/explain
    """
    sym = (symbol or "").strip().upper()
    fetched_at = datetime.now(timezone.utc)

    # --- Inputs (parallel + fail-soft) ---
    # Keep this endpoint responsive: it must return partial artifacts even if one provider is slow.
    errors: list[dict[str, object]] = []

    async def _timed(name: str, coro, timeout_s: float, *, default):
        try:
            return await asyncio.wait_for(coro, timeout=timeout_s)
        except Exception as exc:
            errors.append({"step": name, "error": f"{type(exc).__name__}: {exc}"})
            return default

    inst_task = asyncio.create_task(_timed("instrument_summary", instrument_summary(sym, service=market), 8.0, default={}))
    ohlcv_task = asyncio.create_task(
        _timed("ohlcv", market_ohlcv(sym, timeframe=timeframe, limit=limit, service=market), 12.0, default={})
    )
    fund_task = asyncio.create_task(_timed("fundamentals_dashboard", fundamentals.build_dashboard(sym, years=int(years)), 15.0, default=None))
    gov_task = asyncio.create_task(
        _timed("governance_dashboard", governance.build_dashboard(sym, int(gov_year), int(gov_quarter)), 12.0, default=None)
    )
    nar_task = asyncio.create_task(
        _timed("analyst_narrative", governance.analyst_narrative(sym, int(gov_year), int(gov_quarter)), 10.0, default={})
    )
    peers_task = asyncio.create_task(
        _timed("peers", peer_comparison(sym, extra=str(peers_extra or "")), 20.0, default={})
    )
    mc_task = asyncio.create_task(_timed("market_context_feed", market_context_feed_route(sym, svc=market_context), 12.0, default={}))
    macro_task = asyncio.create_task(_timed("macro_rates", current_rates(), 6.0, default={}))

    inst, ohlcv_payload, fund_dto, gov_dto, nar_payload, peers_payload, mc_feed_payload, macro_rates_payload = await asyncio.gather(
        inst_task, ohlcv_task, fund_task, gov_task, nar_task, peers_task, mc_task, macro_task
    )

    fund_payload = fund_dto.model_dump(mode="json") if fund_dto is not None else {}
    gov_payload = gov_dto.model_dump(mode="json") if gov_dto is not None else {}

    missing = {
        "instrument_summary": not bool(inst),
        "ohlcv": not bool(ohlcv_payload),
        "fundamentals": not bool(fund_payload),
        "governance": not bool(gov_payload),
        "analyst_narrative": not bool(nar_payload),
        "peers": not bool(peers_payload),
        "market_context_feed": not bool(mc_feed_payload),
        "macro_rates": not bool(macro_rates_payload),
    }

    # --- Verdicts (server-side, parallel + fail-soft) ---
    val_task = asyncio.create_task(
        _timed(
            "valuation_verdict",
            valuation_verdict(
                sym,
                years=int(years),
                include_explain=bool(include_explain),
                mos_required=float(mos_required),
                premium_threshold=float(premium_threshold),
                wacc_span=float(wacc_span),
                terminal_span=float(terminal_span),
                grid_size=int(grid_size),
                fundamentals=fundamentals,
                market=market,
            ),
            20.0,
            default={},
        )
    )
    chart_task = asyncio.create_task(
        _timed(
            "chart_technical_verdict",
            chart_technical_verdict_route(sym, timeframe=timeframe, limit=int(limit), service=market),
            12.0,
            default={},
        )
    )
    mc_verdict = build_market_context_verdict(
        symbol=sym, feed=mc_feed_payload if isinstance(mc_feed_payload, dict) else None
    )
    val_payload, chart_payload = await asyncio.gather(val_task, chart_task)

    # --- Stock360 composition ---
    stock360 = compose_stock360(
        symbol=sym,
        valuation_verdict=val_payload if isinstance(val_payload, dict) else None,
        chart_verdict=chart_payload if isinstance(chart_payload, dict) else None,
        market_context_verdict=mc_verdict if isinstance(mc_verdict, dict) else None,
        include_explain=bool(include_explain),
    )

    return {
        "ok": True,
        "symbol": sym,
        "meta": {
            "artifact_version": "v1",
            "fetched_at_utc": fetched_at.isoformat(),
            "config": {
                "include_explain": bool(include_explain),
                "timeframe": timeframe.value,
                "limit": int(limit),
                "years": int(years),
                "gov_year": int(gov_year),
                "gov_quarter": int(gov_quarter),
                "peers_extra": str(peers_extra or ""),
                "valuation": {
                    "mos_required": float(mos_required),
                    "premium_threshold": float(premium_threshold),
                    "wacc_span": float(wacc_span),
                    "terminal_span": float(terminal_span),
                    "grid_size": int(grid_size),
                },
            },
            "missing": missing,
            "errors": errors,
            "notes": [
                "All tabs should render from this artifact (no per-tab API calls).",
                "Stock360 is composed from verdicts and keeps traceability to raw inputs.",
            ],
        },
        "inputs": {
            "instrument_summary": inst,
            "ohlcv": ohlcv_payload,
            "fundamentals": fund_payload,
            "governance": gov_payload,
            "analyst_narrative": nar_payload,
            "peers": peers_payload,
            "market_context_feed": mc_feed_payload,
            "macro_rates": macro_rates_payload,
        },
        "verdicts": {
            "valuation_verdict": val_payload,
            "chart_technical_verdict": chart_payload,
            "market_context_verdict": mc_verdict,
        },
        "stock360": stock360,
    }

