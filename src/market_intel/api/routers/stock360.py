from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends

from market_intel.api.dependencies import get_fundamentals_service, get_governance_service, get_market_service
from market_intel.application.services.fundamentals_service import FundamentalsService
from market_intel.application.services.governance_service import GovernanceService
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.api.routers.peers import peer_comparison as peers_comparison
from market_intel.api.routers.instruments import instrument_summary
from market_intel.modules.analytics.stock360_forecast_core import compute_final_verdict_payload

router = APIRouter(prefix="/stock360", tags=["stock360"])


def _dbg(hypothesis_id: str, location: str, message: str, data: dict[str, object]) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": "292cf3",
            "runId": "entry-debug",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        Path("debug-292cf3.log").open("a", encoding="utf-8").write(
            json.dumps(payload, ensure_ascii=False) + "\n"
        )
    except Exception:
        pass
    # #endregion


@router.get("/{symbol}/bundle")
async def stock360_bundle(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    limit: int = 320,
    years: int = 10,
    gov_year: int = 2024,
    gov_quarter: int = 4,
    include_explain: bool = True,
    market: MarketDataService = Depends(get_market_service),
    fundamentals: FundamentalsService = Depends(get_fundamentals_service),
    governance: GovernanceService = Depends(get_governance_service),
) -> dict[str, Any]:
    sym = (symbol or "").strip().upper()

    # Instruments summary (already an endpoint; reuse its logic)
    inst = await instrument_summary(sym, service=market)

    # Technical
    df = await market.historical_frame(sym, timeframe, limit)
    candles = market.candles_to_dto(df)
    patterns = market.detect_patterns(df)
    indicators = market.indicator_bundle(df)
    technical = {
        "symbol": sym,
        "timeframe": timeframe.value,
        "candles": [c.model_dump(mode="json") for c in candles],
        "patterns": [p.model_dump() for p in patterns],
        "indicators": indicators,
    }

    # Fundamentals
    dash = await fundamentals.build_dashboard(sym, years=years)
    fundamentals_payload = dash.model_dump(mode="json")
    if not include_explain:
        fundamentals_payload.pop("wacc_explain", None)
        fundamentals_payload.pop("dcf_explain", None)
        # forensic flag explain can be large; keep it only when include_explain
        for f in fundamentals_payload.get("forensic_flags") or []:
            if isinstance(f, dict):
                f.pop("explain", None)

    # Governance
    gov_dto = await governance.build_dashboard(sym, gov_year, gov_quarter)
    gov_payload = gov_dto.model_dump(mode="json")
    nar = await governance.analyst_narrative(sym, gov_year, gov_quarter)
    if not include_explain and isinstance(nar, dict):
        nar.pop("meta", None)

    peers_payload = await peers_comparison(sym, extra="")

    return {
        "symbol": sym,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "instrument_summary": inst,
        "technical": technical,
        "fundamentals": fundamentals_payload,
        "governance": gov_payload,
        "analyst_narrative": nar,
        "peers": peers_payload,
    }


@router.get("/{symbol}/final-verdict")
async def final_verdict(
    symbol: str,
    horizon_days: str = "30,90,365",
    include_explain: bool = True,
    market: MarketDataService = Depends(get_market_service),
    fundamentals: FundamentalsService = Depends(get_fundamentals_service),
    governance: GovernanceService = Depends(get_governance_service),
) -> dict[str, Any]:
    """
    Final verdict endpoint: targets (1M/3M/1Y), probabilities, risks, and required entry price.
    ML approach (no external deps): per-horizon linear regression on engineered features with
    normal residual approximation for probabilities. Fully transparent via explain payload.
    """
    _ = governance  # dependency parity / future hooks
    sym = (symbol or "").strip().upper()
    horizons_cal: list[int] = []
    for p in (horizon_days or "").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            horizons_cal.append(int(p))
        except ValueError:
            continue
    horizons_cal = [h for h in horizons_cal if h > 1]
    if not horizons_cal:
        horizons_cal = [30, 90, 365]

    inst = await instrument_summary(sym, service=market)

    df = await market.historical_frame(sym, Timeframe.D1, limit=1100)
    if df.empty or "close" not in df:
        return {"ok": False, "symbol": sym, "message": "No price history available."}

    indicators = market.indicator_bundle(df)

    dash = await fundamentals.build_dashboard(sym, years=10)
    fund = dash.model_dump(mode="json")

    peers_payload = await peers_comparison(sym, extra="")

    return compute_final_verdict_payload(
        sym=sym,
        df=df,
        fund=fund,
        inst=inst,
        horizons_cal=horizons_cal,
        indicators=indicators,
        peers_payload=peers_payload,
        include_explain=include_explain,
    )
