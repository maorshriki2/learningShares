from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal


FinalLabel = Literal["buy", "hold", "sell", "watch"]
Direction = Literal["up", "down_or_flat", "mixed", "unknown"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compose_stock360(
    *,
    symbol: str,
    valuation_verdict: dict[str, Any] | None,
    chart_verdict: dict[str, Any] | None,
    market_context_verdict: dict[str, Any] | None,
    include_explain: bool,
) -> dict[str, Any]:
    """
    Compose a Stock360 final verdict from 3 domain verdicts.
    This is intentionally simple and transparent (rule-based) for v1.
    """
    sym = (symbol or "").strip().upper()
    reasons: list[str] = []
    risks: list[str] = []
    trace: dict[str, Any] = {"sources": {}}

    # --- Valuation ---
    v_label = None
    required_entry_price = None
    if isinstance(valuation_verdict, dict):
        v = valuation_verdict.get("verdict") if isinstance(valuation_verdict.get("verdict"), dict) else None
        v_label = str((v or {}).get("label") or "").strip().lower() or None
        try:
            required_entry_price = (v or {}).get("required_entry_price")
            required_entry_price = float(required_entry_price) if required_entry_price is not None else None
        except Exception:
            required_entry_price = None
    trace["sources"]["valuation_verdict_label"] = v_label

    # --- Chart technical ---
    c_score = None
    c_stance = None
    if isinstance(chart_verdict, dict):
        snap = chart_verdict.get("snapshot") if isinstance(chart_verdict.get("snapshot"), dict) else None
        c_stance = str((snap or {}).get("stance_he") or "").strip() or None
        try:
            c_score = (snap or {}).get("score")
            c_score = int(c_score) if c_score is not None else None
        except Exception:
            c_score = None
    trace["sources"]["chart_score"] = c_score
    trace["sources"]["chart_stance_he"] = c_stance

    # --- Market context ---
    mc_signal = None
    if isinstance(market_context_verdict, dict):
        mc_signal = str(market_context_verdict.get("signal") or "").strip().lower() or None
    trace["sources"]["market_context_signal"] = mc_signal

    # --- Simple scoring / rules (v2: stronger gating + confidence) ---
    score = 0
    if v_label == "buy":
        score += 2
        reasons.append("הערכת שווי מצביעה על MOS ומחיר כניסה בהתאם (Valuation: Buy).")
    elif v_label == "hold":
        score += 0
        reasons.append("הערכת שווי אינה מובהקת (Valuation: Hold).")
    elif v_label == "sell":
        score -= 2
        reasons.append("הערכת שווי מצביעה על פרמיה משמעותית (Valuation: Sell).")
    else:
        risks.append("אין Verdict פונדמנטלי-תמחורי זמין — הוודאות יורדת.")

    if c_score is not None:
        if c_score >= 2:
            score += 1
            reasons.append("הגרף מצביע על נטייה חיובית בחלון הנוכחי (Chart: positive).")
        elif c_score <= -2:
            score -= 1
            reasons.append("הגרף מצביע על נטייה שלילית בחלון הנוכחי (Chart: negative).")
        else:
            reasons.append("הגרף מצביע על מצב מעורב/נייטרלי (Chart: mixed).")
    else:
        risks.append("אין Snapshot טכני זמין — הוודאות יורדת.")

    if mc_signal == "bullish":
        score += 1
        reasons.append("הקשר שוק/רשת מצביע על סנטימנט חיובי (Context: bullish).")
    elif mc_signal == "bearish":
        score -= 1
        reasons.append("הקשר שוק/רשת מצביע על סנטימנט שלילי (Context: bearish).")
    elif mc_signal in ("neutral", "mixed"):
        reasons.append("הקשר שוק/רשת לא מובהק (Context: neutral).")
    elif mc_signal in ("not_ready", None, ""):
        risks.append("שכבת Market Context עדיין לא מסיקה סיגנל אמין — מתעלמים/מורידים משקל.")

    # Hard gates: don't allow Buy if valuation says Sell.
    if v_label == "sell" and score >= 2:
        score = min(score, 1)
        risks.append("Gate: Valuation=Sell מגביל מסקנה שורית למרות אותות אחרים.")

    # Direction + label mapping
    direction: Direction = "unknown"
    if score >= 2:
        direction = "up"
    elif score <= -2:
        direction = "down_or_flat"
    else:
        direction = "mixed"

    final_label: FinalLabel = "watch"
    if score >= 3:
        final_label = "buy"
    elif score <= -3:
        final_label = "sell"
    else:
        final_label = "hold"

    # Confidence heuristic: based on presence + agreement
    present = 0
    agree = 0
    if v_label in ("buy", "hold", "sell"):
        present += 1
        agree += 1 if (v_label == "buy" and score > 0) or (v_label == "sell" and score < 0) or (v_label == "hold") else 0
    if c_score is not None:
        present += 1
        agree += 1 if (c_score >= 2 and score > 0) or (c_score <= -2 and score < 0) or (-1 <= c_score <= 1) else 0
    if mc_signal and mc_signal != "not_ready":
        present += 1
        agree += 1 if (mc_signal == "bullish" and score > 0) or (mc_signal == "bearish" and score < 0) or (mc_signal in ("neutral", "mixed")) else 0
    confidence = None
    if present:
        confidence = max(0.2, min(0.95, 0.25 + 0.25 * (agree / float(present)) + 0.15 * (present - 1)))

    out: dict[str, Any] = {
        "ok": True,
        "symbol": sym,
        "fetched_at_utc": _now(),
        "final_label": final_label,
        "direction": direction,
        "confidence": confidence,
        "key_reasons_he": reasons[:8],
        "risks_he": risks[:8],
        "required_entry_price": required_entry_price,
        "trace": trace,
    }
    if include_explain:
        out["explain"] = {
            "score": score,
            "weights": {"valuation": 2, "chart": 1, "context": 1},
            "inputs_present": {
                "valuation": bool(v_label),
                "chart": c_score is not None,
                "context": bool(mc_signal) and mc_signal != "not_ready",
            },
        }
    return out

