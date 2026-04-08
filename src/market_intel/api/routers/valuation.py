from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import math
import json
from pathlib import Path
import numpy as np
from fastapi import APIRouter, Depends, Query

from market_intel.api.dependencies import get_fundamentals_service, get_market_service
from market_intel.application.services.fundamentals_service import FundamentalsService
from market_intel.application.services.market_data_service import MarketDataService
from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.modules.fundamentals.valuation.dcf_sensitivity import build_dcf_sensitivity_matrix

router = APIRouter(prefix="/valuation", tags=["valuation"])


def _dbg(hypothesis_id: str, message: str, data: dict[str, Any]) -> None:
    # #region agent log
    try:
        p = Path(r"c:\Projects\learn_shares\debug-a73902.log")
        payload = {
            "sessionId": "a73902",
            "runId": "server",
            "hypothesisId": hypothesis_id,
            "location": "api/routers/valuation.py",
            "message": message,
            "data": data,
            "timestamp": int(__import__("time").time() * 1000),
        }
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion


def _finite_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _percentiles_from_matrix(mat: list[list[float | None]]) -> dict[str, float | None]:
    vals: list[float] = []
    for row in mat:
        for cell in row:
            if cell is None:
                continue
            try:
                v = float(cell)
            except (TypeError, ValueError):
                continue
            if math.isfinite(v):
                vals.append(v)
    if not vals:
        return {"p10": None, "p50": None, "p90": None}
    a = np.asarray(vals, dtype=float)
    return {
        "p10": float(np.percentile(a, 10)),
        "p50": float(np.percentile(a, 50)),
        "p90": float(np.percentile(a, 90)),
    }


@router.get("/{symbol}/verdict")
async def valuation_verdict(
    symbol: str,
    years: int = 10,
    include_explain: bool = True,
    mos_required: float = Query(default=0.15, ge=0.0, le=0.6),
    premium_threshold: float = Query(default=0.15, ge=0.0, le=1.0),
    wacc_span: float = Query(default=0.02, ge=0.0, le=0.2),
    terminal_span: float = Query(default=0.01, ge=0.0, le=0.1),
    grid_size: int = Query(default=5, ge=3, le=9),
    fundamentals: FundamentalsService = Depends(get_fundamentals_service),
    market: MarketDataService = Depends(get_market_service),
) -> dict[str, Any]:
    """
    Stable, DCF/WACC-centric valuation verdict.
    This endpoint is intentionally independent of Stock360 so UI won't break if Stock360 evolves.
    """
    sym = (symbol or "").strip().upper()
    _dbg(
        "S1",
        "valuation_verdict_called",
        {
            "symbol": sym,
            "years": int(years),
            "include_explain": bool(include_explain),
            "mos_required": float(mos_required),
            "premium_threshold": float(premium_threshold),
            "wacc_span": float(wacc_span),
            "terminal_span": float(terminal_span),
            "grid_size": int(grid_size),
        },
    )
    dash = await fundamentals.build_dashboard(sym, years=int(years))
    d = dash.model_dump(mode="json")

    # Current price from market history (fallback if missing in dashboard)
    df = await market.historical_frame(sym, Timeframe.D1, limit=6)
    current_price = float(df["close"].astype(float).iloc[-1]) if (not df.empty and "close" in df) else None
    if current_price is None:
        current_price = _finite_float(d.get("market_price"))

    wacc = _finite_float(d.get("wacc"))
    roic = _finite_float(d.get("roic_latest"))
    dcf_base = d.get("dcf_base") if isinstance(d.get("dcf_base"), dict) else {}
    intrinsic = _finite_float(dcf_base.get("intrinsic_per_share"))
    pv_terminal = None
    ev = None
    try:
        dcf_explain = d.get("dcf_explain") if isinstance(d.get("dcf_explain"), dict) else None
        pv_terminal = _finite_float(dcf_explain.get("pv_terminal")) if dcf_explain else None
        ev = _finite_float(dcf_explain.get("enterprise_value")) if dcf_explain else None
    except Exception:
        pv_terminal, ev = None, None

    mos_pct = None
    if current_price is not None and intrinsic is not None and current_price > 0:
        mos_pct = (intrinsic - current_price) / current_price

    required_entry_price = None
    if intrinsic is not None:
        required_entry_price = intrinsic * (1.0 - float(mos_required))

    # Sensitivity ranges (percentiles across valid cells)
    sens = d.get("dcf_sensitivity") if isinstance(d.get("dcf_sensitivity"), dict) else None
    if sens and isinstance(sens.get("intrinsic_per_share_matrix"), list):
        w_axis = sens.get("wacc_values") or []
        t_axis = sens.get("terminal_growth_values") or []
        mat = sens.get("intrinsic_per_share_matrix") or []
    else:
        # rebuild quickly from dashboard base inputs
        base_fcf = None
        try:
            dcf_explain = d.get("dcf_explain") if isinstance(d.get("dcf_explain"), dict) else None
            base_fcf = _finite_float(dcf_explain.get("base_free_cash_flow")) if dcf_explain else None
        except Exception:
            base_fcf = None
        base_fcf = float(base_fcf) if base_fcf is not None else 1.0
        shares = None
        try:
            shares = _finite_float((d.get("dcf_explain") or {}).get("shares_outstanding"))
        except Exception:
            shares = None
        net_debt = 0.0
        growth_high = _finite_float(dcf_base.get("growth_high")) or 0.05
        base_wacc = float(wacc) if wacc is not None else 0.09
        base_tg = _finite_float(dcf_base.get("terminal_growth")) or 0.02
        w_axis, t_axis, mat = build_dcf_sensitivity_matrix(
            base_free_cash_flow=base_fcf,
            shares_outstanding=shares,
            net_debt=net_debt,
            growth_years_1_to_5=float(growth_high),
            base_wacc=float(base_wacc),
            base_terminal_growth=float(base_tg),
            wacc_half_span=float(wacc_span),
            terminal_half_span=float(terminal_span),
            grid_size=int(grid_size),
        )

    ranges = _percentiles_from_matrix(mat if isinstance(mat, list) else [])

    # Sanity checks
    terminal_growth = _finite_float(dcf_base.get("terminal_growth"))
    terminal_growth_lt_wacc = None
    if terminal_growth is not None and wacc is not None:
        terminal_growth_lt_wacc = terminal_growth < wacc

    terminal_weight_pct = None
    if pv_terminal is not None and ev is not None and ev > 0:
        terminal_weight_pct = pv_terminal / ev

    terminal_weight_flag = "ok"
    if terminal_weight_pct is not None and terminal_weight_pct > 0.80:
        terminal_weight_flag = "warn"

    # Verdict rules (transparent)
    reasons: list[str] = []
    label = "hold"
    if current_price is None or intrinsic is None:
        label = "hold"
        reasons.append("Missing price or intrinsic → default Hold.")
    else:
        if required_entry_price is not None and current_price <= required_entry_price:
            label = "buy"
            reasons.append("Price <= required_entry_price (MOS rule) → Buy.")
        elif current_price >= intrinsic * (1.0 + float(premium_threshold)):
            label = "sell"
            reasons.append("Price >= intrinsic*(1+premium_threshold) → Sell.")
        else:
            label = "hold"
            reasons.append("Price between entry and premium thresholds → Hold.")

    # Downgrade rules
    if terminal_weight_flag == "warn":
        if label == "buy":
            label = "hold"
            reasons.append("Terminal weight > 80% → downgrade Buy→Hold.")
        elif label == "hold":
            reasons.append("Terminal weight > 80% → warning (fragile DCF).")

    if roic is not None and wacc is not None and roic < wacc:
        if label == "buy":
            label = "hold"
            reasons.append("ROIC < WACC → downgrade Buy→Hold (quality check).")
        elif label == "hold":
            reasons.append("ROIC < WACC → warning (value creation not evident).")

    verdict = {
        "label": label,
        "current_price": current_price,
        "intrinsic_per_share_base": intrinsic,
        "mos_pct": mos_pct,
        "required_entry_price": required_entry_price,
        "reasons": reasons,
    }

    out: dict[str, Any] = {
        "ok": True,
        "symbol": sym,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "sanity_checks": {
            "terminal_growth_lt_wacc": terminal_growth_lt_wacc,
            "terminal_weight_pct": terminal_weight_pct,
            "terminal_weight_flag": terminal_weight_flag,
            "roic_lt_wacc": (roic < wacc) if (roic is not None and wacc is not None) else None,
        },
        "ranges": ranges,
    }

    if include_explain:
        out["explain"] = {
            "assumptions": {
                "years": int(years),
                "mos_required": float(mos_required),
                "premium_threshold": float(premium_threshold),
                "wacc_span": float(wacc_span),
                "terminal_span": float(terminal_span),
                "grid_size": int(grid_size),
            },
            "rules": {
                "buy_if_price_lte_entry": True,
                "sell_if_price_gte_intrinsic_premium": float(premium_threshold),
                "downgrade_if_terminal_weight_gt": 0.80,
                "downgrade_if_roic_lt_wacc": True,
            },
            "fundamentals_fields": {
                "wacc": wacc,
                "roic_latest": roic,
                "terminal_growth": terminal_growth,
            },
            "wacc_explain": d.get("wacc_explain"),
            "dcf_explain": d.get("dcf_explain"),
            "sensitivity": {
                "wacc_values": w_axis,
                "terminal_growth_values": t_axis,
                "intrinsic_per_share_matrix": mat,
            },
        }

    return out

