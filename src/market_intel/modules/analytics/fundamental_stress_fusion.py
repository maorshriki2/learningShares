"""
When short-horizon ML implies 'up' but quality/MOS/forensics imply severe distress,
override the public verdict direction (educational fusion — not investment advice).
"""

from __future__ import annotations

from typing import Any

import math


def _ff(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def fundamental_stress_bearish(fund: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Heuristic 'Enron-like' screen: multiple independent red signals together.
    """
    reasons: list[str] = []
    roic = _ff(fund.get("roic_latest"))
    wacc = _ff(fund.get("wacc"))
    mos = _ff(fund.get("margin_of_safety_pct"))
    az = _ff(fund.get("altman_z"))
    if az is None:
        az = _ff(fund.get("altman_z_score"))

    pi_raw = fund.get("piotroski_score")
    try:
        pi = int(pi_raw) if pi_raw is not None else None
    except (TypeError, ValueError):
        pi = None

    flags = fund.get("forensic_flags") or []
    n_high = sum(1 for f in flags if isinstance(f, dict) and f.get("severity") == "high")

    score = 0
    if az is not None and az < 1.81:
        score += 2
        reasons.append("`Altman Z` מתחת ל־`1.81` — אזור סיכון")
    if pi is not None and pi <= 3:
        score += 1
        reasons.append("`Piotroski` עד `3` — מבנה חלש")
    if mos is not None and mos < -15:
        score += 1
        reasons.append("`MOS` שלילי חזק (מתחת ל־`-15%`)")
    if roic is not None and wacc is not None and (roic - wacc) < -0.05:
        score += 1
        reasons.append("`ROIC` נמוך מ־`WACC` במובהק")
    if n_high >= 1:
        score += 1
        reasons.append("דגל פורנזיקה ברמת `high`")

    # Trigger: strong multi-signal (e.g. Enron) or Altman+Piotroski+MOS all bad
    bearish = score >= 4 or (score >= 3 and az is not None and az < 1.81 and pi is not None and pi <= 3)
    # Backup if Piotroski missing from payload but distress is extreme (Altman + deep negative MOS)
    if not bearish and az is not None and az < 1.81 and mos is not None and mos < -15:
        bearish = True
        reasons.append("`Altman` בסיכון + `MOS` שלילי חזק (בלי `Piotroski`)")
    return bearish, reasons


def apply_fundamental_stress_fusion(verdict: dict[str, Any], fund: dict[str, Any]) -> None:
    """
    Mutates verdict in place when stress triggers: direction down_or_flat + softer upside probs.
    """
    bearish, reasons = fundamental_stress_bearish(fund)
    if not bearish:
        verdict["fundamental_stress_active"] = False
        return

    verdict["fundamental_stress_active"] = True
    verdict["fundamental_stress_reasons_he"] = reasons
    verdict["fundamental_stress_no_entry_he"] = (
        "**לא להיכנס כהשקעה לפי המסך הזה.** "
        "המערכת מזהה **מצוקה פיננסית חריפה** (איכות / תמחור / פורנזיקה). "
        "בהקשר חינוכי זה מסווג כ**סיכון גבוה מאוד** — לא כהזדמנות."
    )
    verdict["fundamental_stress_trading_gate_he"] = (
        "**שער מסחר (חינוכי):** במקרה כזה אין המלצת כניסה; "
        "המטרה היא לזהות אותות אזהרה ולעצור לפני החלטה."
    )
    verdict["forecast_direction_ml_raw"] = verdict.get("forecast_direction")
    verdict["forecast_direction"] = "down_or_flat"

    probs = verdict.get("probabilities") or {}
    for obj in probs.values():
        if not isinstance(obj, dict):
            continue
        up = _ff(obj.get("p_return_positive"))
        if up is not None:
            obj["p_return_positive"] = min(float(up) * 0.45, 0.33)
        dn = _ff(obj.get("p_return_below_-10pct"))
        if dn is not None:
            obj["p_return_below_-10pct"] = min(0.95, float(dn) + 0.12)

    verdict["fundamental_stress_note_he"] = (
        "מודל קצר־טווח על דפוסי מחיר; כאן הופעלה **תאימות פנדמנטלית**. "
        "כיוון מותאם ל־`down_or_flat` ולא ל־`up` בלבד כשיש מצוקה חמורה."
    )
