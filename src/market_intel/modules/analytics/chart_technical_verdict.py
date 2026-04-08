"""
Backend chart-only verdict computation.

This is the server-side counterpart of the UI snapshot builder so that:
- the analysis artifact can depend on it
- Stock360 can compose from a consistent, versioned chart verdict

Educational only (not investment advice).
"""

from __future__ import annotations

import math
from typing import Any


def _to_f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _candle_close(c: Any) -> float | None:
    if isinstance(c, dict):
        return _to_f(c.get("close"))
    return _to_f(getattr(c, "close", None))


def _candle_vol(c: Any) -> float | None:
    if isinstance(c, dict):
        return _to_f(c.get("volume"))
    return _to_f(getattr(c, "volume", None))


def _last_numeric(seq: list[Any] | None) -> tuple[int, float] | None:
    if not seq:
        return None
    for i in range(len(seq) - 1, -1, -1):
        v = _to_f(seq[i])
        if v is not None:
            return i, v
    return None


def _last_dual_aligned(a: list[Any] | None, b: list[Any] | None) -> tuple[int, float, float] | None:
    if not a or not b or len(a) != len(b):
        return None
    for i in range(len(a) - 1, -1, -1):
        va, vb = _to_f(a[i]), _to_f(b[i])
        if va is not None and vb is not None:
            return i, va, vb
    return None


_PATTERN_HE: dict[str, str] = {
    "head_and_shoulders": "ראש וכתפיים",
    "bull_flag": "דגל שורי",
}


def build_chart_technical_snapshot(
    *,
    candles: list[Any],
    indicators: dict[str, Any],
    patterns: list[Any],
    fibonacci: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Deterministic summary from the same payload as `/api/v1/market/{symbol}/ohlcv`.
    Returns a compact snapshot suitable for:
    - Chart Technical Verdict tab
    - Stock 360 composition layer
    """

    closes = [_candle_close(c) for c in candles]
    closes_n = [c for c in closes if c is not None]
    first_c = closes_n[0] if closes_n else None
    last_c = closes_n[-1] if closes_n else None
    window_ret = None
    if first_c and last_c and first_c > 0:
        window_ret = (last_c / first_c) - 1.0

    rsi_s = indicators.get("rsi14") if isinstance(indicators, dict) else None
    rsi_seq = rsi_s if isinstance(rsi_s, list) else []
    rsi_last = _last_numeric(rsi_seq)
    rsi_val = rsi_last[1] if rsi_last else None
    if rsi_val is None:
        rsi_zone = "—"
    elif rsi_val >= 70:
        rsi_zone = "אזור חזק (מעל 70)"
    elif rsi_val <= 30:
        rsi_zone = "אזור חלש (מתחת ל‑30)"
    else:
        rsi_zone = "בינוני"

    macd = indicators.get("macd") if isinstance(indicators, dict) else None
    sig = indicators.get("macd_signal") if isinstance(indicators, dict) else None
    macd_line = macd if isinstance(macd, list) else []
    sig_line = sig if isinstance(sig, list) else []
    dual = _last_dual_aligned(macd_line, sig_line)
    macd_hint = "—"
    hist_hint = ""
    hist_s = indicators.get("macd_histogram") if isinstance(indicators, dict) else None
    hist_line = hist_s if isinstance(hist_s, list) else []
    hi = _last_numeric(hist_line)
    if dual:
        _, m_val, s_val = dual
        if m_val > s_val:
            macd_hint = "MACD מעל קו הסיגנל (מומנטום שורי יחסית)"
        elif m_val < s_val:
            macd_hint = "MACD מתחת לקו הסיגנל (מומנטום דובי יחסית)"
        else:
            macd_hint = "MACD על קו הסיגנל"
    if hi:
        hv = hi[1]
        hist_hint = f" היסטוגרם אחרון: {hv:+.4f}."

    vwap_s = indicators.get("vwap") if isinstance(indicators, dict) else None
    vwap_line = vwap_s if isinstance(vwap_s, list) else None
    vwap_hint = "—"
    if last_c is not None and isinstance(vwap_line, list):
        vi = _last_numeric(vwap_line)
        if vi:
            vv = vi[1]
            if vv > 0:
                diff = (last_c / vv) - 1.0
                if diff > 0.005:
                    vwap_hint = f"סגירה מעל VWAP ב‑~{abs(diff)*100:.2f}%"
                elif diff < -0.005:
                    vwap_hint = f"סגירה מתחת ל‑VWAP ב‑~{abs(diff)*100:.2f}%"
                else:
                    vwap_hint = "סגירה ליד VWAP"

    ten = indicators.get("ichimoku_tenkan") if isinstance(indicators, dict) else None
    kij = indicators.get("ichimoku_kijun") if isinstance(indicators, dict) else None
    ten_l = ten if isinstance(ten, list) else []
    kij_l = kij if isinstance(kij, list) else []
    ichi_dual = _last_dual_aligned(ten_l, kij_l)
    ichi_hint = "—"
    if ichi_dual:
        _, t_val, k_val = ichi_dual
        if t_val > k_val:
            ichi_hint = "טנקן מעל קיגון — מגמה קצרת־טווח חיובית יחסית באינדיקטור"
        elif t_val < k_val:
            ichi_hint = "טנקן מתחת לקיגון — מגמה קצרת־טווח שלילית יחסית באינדיקטור"
        else:
            ichi_hint = "טנקן וקיגון מתלכדים"

    vols = [_candle_vol(c) for c in candles[-20:]]
    vols_n = [v for v in vols if v is not None and v >= 0]
    last_v = _candle_vol(candles[-1]) if candles else None
    vol_hint = "—"
    if vols_n and last_v is not None:
        avg_v = sum(vols_n) / len(vols_n)
        if avg_v > 0:
            if last_v > avg_v * 1.25:
                vol_hint = "נפח אחרון מעל ממוצע 20 תקופות (פעילות יחסית גבוהה)"
            elif last_v < avg_v * 0.75:
                vol_hint = "נפח אחרון מתחת לממוצע 20 תקופות (ריכוך יחסי)"

    fib_hint = None
    if fibonacci and last_c is not None:
        levels = fibonacci.get("levels")
        if isinstance(levels, dict) and levels:
            fib_hint = "רמות פיבונאצ’י זמינות — השוו סגירה אחרונה למסגרת הנסיגה בגרף."

    pattern_bullets: list[str] = []
    for p in patterns or []:
        if isinstance(p, dict):
            name = str(p.get("name") or "")
            conf = _to_f(p.get("confidence"))
        else:
            name = str(getattr(p, "name", "") or "")
            conf = _to_f(getattr(p, "confidence", None))
        he = _PATTERN_HE.get(name, name or "תבנית")
        if conf is not None:
            pattern_bullets.append(f"{he} (ביטחון ~{conf:.2f})")
        elif name:
            pattern_bullets.append(he)

    # Shallow stance from chart-only signals (educational).
    score = 0
    if window_ret is not None:
        if window_ret > 0.015:
            score += 1
        elif window_ret < -0.015:
            score -= 1
    if dual:
        _, mv, sv = dual
        if mv > sv:
            score += 1
        elif mv < sv:
            score -= 1
    if last_c is not None and isinstance(vwap_line, list):
        vi = _last_numeric(vwap_line)
        if vi and vi[1] > 0:
            if last_c > vi[1] * 1.002:
                score += 1
            elif last_c < vi[1] * 0.998:
                score -= 1
    if rsi_val is not None:
        if rsi_val >= 72:
            score -= 1
        elif rsi_val <= 28:
            score += 1

    if score >= 2:
        stance = "נטייה חיובית (גרף בלבד)"
    elif score <= -2:
        stance = "נטייה שלילית (גרף בלבד)"
    else:
        stance = "מעורב / נייטרלי (גרף בלבד)"

    return {
        "stance_he": stance,
        "window_return_pct": window_ret * 100 if window_ret is not None else None,
        "rsi_value": rsi_val,
        "rsi_zone": rsi_zone,
        "macd_hint_he": macd_hint + hist_hint,
        "vwap_hint_he": vwap_hint,
        "ichimoku_hint_he": ichi_hint,
        "volume_hint_he": vol_hint,
        "fib_hint_he": fib_hint,
        "pattern_bullets": pattern_bullets,
        "n_bars": len(candles),
        "score": score,
    }

