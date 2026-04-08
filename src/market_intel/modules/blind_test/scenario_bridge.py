"""
Map blind case-study payloads (CSV/API) into OHLCV + fundamentals-shaped dicts
so the same Stock 360 forecast core and UI narratives can run.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def blind_study_to_ohlcv_df(study: dict[str, Any]) -> pd.DataFrame:
    """
    Interpolate monthly-ish blind chart points to a daily close series (enough bars for SMA200).

    **חשוב:** משתמשים רק בנקודות עם offset_months ≤ 0 (היסטוריה עד ה-snapshot).
    נקודות "עתיד" בגרף (למשל קריסה ל-0 אחרי ה-snapshot) לא יכולות להיות שורת ה-close האחרונה —
    אחרת המודל מזהה "היום" במחיר שגוי (כמו Enron בסוף הסדרה).
    """
    pts_all = sorted(study.get("price_chart_data") or [], key=lambda x: int(x.get("offset_months", 0)))
    pts = [p for p in pts_all if int(p.get("offset_months", 0)) <= 0]
    if len(pts) < 2:
        pts = pts_all
    px0 = float(study.get("price_at_snapshot") or 0)
    if not pts or px0 <= 0:
        return pd.DataFrame()
    months = np.array([float(p["offset_months"]) for p in pts], dtype=float)
    prices = np.array([float(p["price_factor"]) * px0 for p in pts], dtype=float)
    m_days = months * 30.4375
    d_lo, d_hi = float(m_days.min()), float(m_days.max())
    span = d_hi - d_lo
    if span < 400:
        pad = (400.0 - span) / 2.0
        d_lo -= pad
        d_hi += pad
    day_idx = np.arange(math.floor(d_lo), math.ceil(d_hi) + 1, dtype=float)
    interp = np.interp(day_idx, m_days, prices)
    out = pd.DataFrame({"close": interp})
    # indicator_bundle (Ichimoku/VWAP) expects OHLC — synthetic bars from single close path
    out["open"] = out["close"]
    out["high"] = out["close"]
    out["low"] = out["close"]
    # volume must be >0 for VWAP cumsum; synthetic path uses 1.0 per bar
    out["volume"] = 1.0
    return out


def synthetic_inst_from_df(df: pd.DataFrame) -> dict[str, Any]:
    """Approximate annualized vol from synthetic series (same role as instrument_summary.volatility_1y)."""
    if df.empty or "close" not in df:
        return {"symbol": "ANONY", "volatility_1y": 0.30}
    r = df["close"].astype(float).pct_change().dropna()
    if len(r) < 10:
        return {"symbol": "ANONY", "volatility_1y": 0.30}
    win = min(len(r), 252)
    vol = float(r.iloc[-win:].std(ddof=0) * math.sqrt(252.0))
    if not math.isfinite(vol) or vol <= 0:
        vol = 0.30
    return {"symbol": "ANONY", "volatility_1y": min(2.0, max(0.05, vol))}


def build_fund_from_blind_study(study: dict[str, Any]) -> dict[str, Any]:
    """
    Map CSV financials_summary + scores into the same keys Stock 360 reads from fundamentals JSON.
    ROIC approximated as ROA when balance sheet available.
    """
    fin = study.get("financials_summary") or {}
    price = float(study.get("price_at_snapshot") or 0)
    ni = fin.get("net_income_b")
    ta = fin.get("total_assets_b")
    roic = None
    if ni is not None and ta is not None and float(ta) > 0:
        roic = float(ni) / float(ta)
    wacc = 0.10
    spread = (roic - wacc) if roic is not None else -0.02
    mult = 1.0 + max(-0.4, min(0.6, float(spread) * 3.0))
    intrinsic = price * mult if price > 0 else None
    mos_pct = None
    if intrinsic is not None and price > 0:
        mos_pct = (intrinsic - price) / price * 100.0

    flags: list[dict[str, Any]] = []
    az = study.get("altman_z")
    if az is not None and float(az) < 1.81:
        flags.append(
            {
                "severity": "high",
                "title_he": "Altman Z — אזור סיכון",
                "detail_he": f"Z={float(az):.2f} (< 1.81). תואם למסך Fundamentals (פורנזיקה).",
            }
        )
    pi = study.get("piotroski_score")
    if pi is not None and int(pi) <= 3:
        flags.append(
            {
                "severity": "medium",
                "title_he": "Piotroski נמוך",
                "detail_he": f"ציון {int(pi)}/9 — מבנה/מגמה חלשים ביחס למודל הפנימי.",
            }
        )

    az_val = study.get("altman_z")
    return {
        "roic_latest": roic,
        "wacc": wacc,
        "margin_of_safety_pct": mos_pct,
        "altman_z": float(az_val) if az_val is not None else None,
        "piotroski_score": study.get("piotroski_score"),
        "dcf_base": {
            "intrinsic_per_share": intrinsic,
            "terminal_growth": 0.025,
            "growth_high": 0.05,
        },
        "forensic_flags": flags,
    }


def build_blind_dashboard_for_ui(study: dict[str, Any], fund: dict[str, Any]) -> dict[str, Any]:
    """Shape for render_fundamentals_snapshot / forensic (symbol ANONY)."""
    fin = study.get("financials_summary") or {}
    year = int(study.get("year") or 2020)
    rev = fin.get("revenue_b")
    niv = fin.get("net_income_b")
    income: list[dict[str, Any]] = []
    if rev is not None:
        income.extend(
            [
                {"label": "Revenue", "fiscal_year": year - 1, "value": float(rev) * 0.97},
                {"label": "Revenue", "fiscal_year": year, "value": float(rev)},
            ]
        )
    if niv is not None:
        income.extend(
            [
                {"label": "Net Income", "fiscal_year": year - 1, "value": float(niv) * 0.97},
                {"label": "Net Income", "fiscal_year": year, "value": float(niv)},
            ]
        )
    out: dict[str, Any] = {**fund}
    out["symbol"] = "ANONY"
    out["kpi_fiscal_year"] = year
    out["piotroski_score"] = study.get("piotroski_score")
    out["income"] = income
    out["market_price"] = study.get("price_at_snapshot")
    return out
