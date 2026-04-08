from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from market_intel.api.dependencies import get_market_service
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.modules.analytics.stock360_forecast_core import compute_final_verdict_payload
from market_intel.modules.blind_test.case_study_engine import CaseStudyEngine
from market_intel.modules.blind_test.scenario_bridge import (
    blind_study_to_ohlcv_df,
    build_blind_dashboard_for_ui,
    build_fund_from_blind_study,
    synthetic_inst_from_df,
)

router = APIRouter(prefix="/blindtest", tags=["blind-test"])

_engine = CaseStudyEngine()


class RevealBody(BaseModel):
    decision: str
    explanation: str = ""


class ScenarioAnalysisBody(BaseModel):
    """Same shape as GET .../blind (case study payload)."""

    study: dict[str, Any]
    horizon_days: str = Field(default="30,90,365", description="Comma-separated calendar days")
    include_explain: bool = True


@router.get("/list")
async def list_studies() -> dict[str, Any]:
    return {"ids": _engine.list_ids()}


@router.get("/random")
async def random_study() -> dict[str, Any]:
    sid = _engine.random_id()
    return _engine.get_blind(sid)


# Static path must be registered before /{study_id}/... so it is never captured as a study id.
@router.post("/analyze-scenario")
async def analyze_scenario(
    body: ScenarioAnalysisBody,
    market: MarketDataService = Depends(get_market_service),
) -> dict[str, Any]:
    """
    Run the **identical** Stock 360 Final Verdict pipeline on an anonymous CSV/API scenario:
    interpolate price chart → OHLCV, map fundamentals summary → fund dict, indicator bundle, ML horizons.
    """
    study = body.study
    df = blind_study_to_ohlcv_df(study)
    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="לא מספיק נתוני מחיר: ודא ש-price_chart_json מלא וש-price_at_snapshot חיובי.",
        )

    indicators = market.indicator_bundle(df)
    inst = synthetic_inst_from_df(df)
    fund = build_fund_from_blind_study(study)
    dash_ui = build_blind_dashboard_for_ui(study, fund)

    horizons_cal: list[int] = []
    for p in (body.horizon_days or "").split(","):
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

    snap = float(study.get("price_at_snapshot") or 0.0)
    payload = compute_final_verdict_payload(
        sym="ANONY",
        df=df,
        fund=fund,
        inst=inst,
        horizons_cal=horizons_cal,
        indicators=indicators,
        peers_payload=None,
        include_explain=body.include_explain,
        current_price_override=snap if snap > 0 else None,
    )
    if not payload.get("ok"):
        raise HTTPException(status_code=400, detail=str(payload.get("message") or "analyze failed"))

    notes = list((payload.get("model") or {}).get("notes") or [])
    notes.append(
        "תרחיש Blind CSV: סדרת מחיר מבוססת אינטרפולציה מ-price_chart_json; "
        "פנדמנטלים ממופים מסיכום ה-CSV (אותה לוגיקת מודל כמו Stock 360)."
    )
    payload["model"]["notes"] = notes
    payload["blind_dashboard"] = dash_ui
    payload["scenario_source"] = "blind_csv"
    return payload


@router.get("/{study_id}/blind")
async def blind_study(study_id: str) -> dict[str, Any]:
    return _engine.get_blind(study_id)


@router.post("/{study_id}/reveal")
async def reveal_study(study_id: str, body: RevealBody) -> dict[str, Any]:
    return _engine.get_reveal(study_id, body.decision, body.explanation)
