"""
Pedagogical 'researcher view': same narrative pattern as Blind Test reveal
(red-flag bullets + expert synthesis), generated from fundamentals / verdict.

Hebrew + English + numbers: use :func:`md_code` (HTML bdi+code) per project BiDi rules;
render with ``unsafe_allow_html=True`` in Streamlit.
"""

from __future__ import annotations

import math
from typing import Any

from market_intel.ui.components.explanation_blocks import render_focus_block, render_focus_heading
from market_intel.ui.formatters.bidi_text import md_code as C


def _f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def build_red_flag_lines_he(
    *,
    dash: dict[str, Any],
    verdict: dict[str, Any] | None,
    study_financials: dict[str, Any] | None,
    include_forensic_duplicates: bool = True,
) -> list[str]:
    """
    Short Hebrew bullets a student can act on (Reveal-style), built from dashboard + optional CSV fin.
    """
    lines: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        t = s.strip()
        if t and t not in seen:
            seen.add(t)
            lines.append(t)

    if include_forensic_duplicates:
        for flag in dash.get("forensic_flags") or []:
            if not isinstance(flag, dict):
                continue
            title = str(flag.get("title_he") or "").strip()
            detail = str(flag.get("detail_he") or "").strip()
            if title and detail:
                add(f"**{title}**\n\n{detail}")
            elif detail:
                add(detail)
            elif title:
                add(title)

    mos = _f(dash.get("margin_of_safety_pct"))
    if mos is not None and mos <= -15:
        add(
            "**תמחור מול מודל**\n\n"
            f"- {C('MOS')} שלילי: {C(f'{mos:.1f}%')}.\n"
            "- המחיר מעל מה שההנחות נותנות כערך סביר."
        )

    roic = _f(dash.get("roic_latest"))
    wacc = _f(dash.get("wacc"))
    if roic is not None and wacc is not None and (roic - wacc) < -0.02:
        add(
            "**איכות עסקית**\n\n"
            f"- {C('ROIC')}: {C(f'{roic * 100:.1f}%')}.\n"
            f"- {C('WACC')}: {C(f'{wacc * 100:.1f}%')}.\n"
            "- פער שלילי — קשה לדבר על יצירת ערך מעל עלות ההון."
        )

    pi_raw = dash.get("piotroski_score")
    try:
        pi = int(pi_raw) if pi_raw is not None else None
    except (TypeError, ValueError):
        pi = None
    if pi is not None and pi <= 3:
        add(
            "**Piotroski**\n\n"
            f"- ציון: {C(pi)} / {C(9)}.\n"
            "- נחשב חלש — לבדוק מאזן והכנסות לעומק."
        )

    az = _f(dash.get("altman_z"))
    if az is not None and az < 1.81:
        add(
            f"**{C('Altman Z')}**\n\n"
            f"- ערך: {C(f'{az:.2f}')}.\n"
            f"- סף סיכון נפוץ: מתחת ל־{C('1.81')}.\n"
            "- אזור מצוקה במודלים קלאסיים."
        )

    fin = study_financials or {}
    ocf = _f(fin.get("operating_cashflow_b"))
    ni = _f(fin.get("net_income_b"))
    if ocf is not None and ni is not None and ocf < 0 and ni > 0:
        add(
            f"**תזרים מול רווח**\n\n"
            f"- {C('Operating cash flow')}: שלילי.\n"
            f"- {C('Net income')}: חיובי.\n"
            "- אי־התאמה — לבדוק איכות רווח והמרה למזומן."
        )

    pe = _f(fin.get("pe_ratio"))
    if pe is not None and pe > 40:
        add(
            "**מכפיל רווח**\n\n"
            f"- {C('P/E')}: {C(f'~{pe:.0f}')}.\n"
            "- לצד חולשה פנדמנטלית — לא לבלבל עם \"מניה זולה\"."
        )

    if verdict and verdict.get("fundamental_stress_active"):
        for r in verdict.get("fundamental_stress_reasons_he") or []:
            add(str(r))

    return lines


def build_expert_analysis_paragraphs_he(*, dash: dict[str, Any], verdict: dict[str, Any] | None) -> list[str]:
    """Short blocks for the green box; Latin tokens via :func:`md_code`."""
    stress = bool(verdict and verdict.get("fundamental_stress_active"))
    mos = _f(dash.get("margin_of_safety_pct"))
    roic = _f(dash.get("roic_latest"))
    wacc = _f(dash.get("wacc"))
    ml_raw = verdict.get("forecast_direction_ml_raw") if verdict else None
    cur = verdict.get("forecast_direction") if verdict else None

    fusion_parts: list[str] = []
    if ml_raw and cur and ml_raw != cur:
        fusion_parts.append(
            "**מודל מחירים vs פנדמנטלים**\n\n"
            f"- מודל קצר־טווח: {C(ml_raw)}.\n"
            f"- אחרי שילוב: {C(cur)}.\n"
            "- זו נקודת לימוד."
        )

    if stress:
        out = [
            "**ניתוח חוקר**\n\n"
            "- כמה אותות נפרדים מצביעים על מצוקה כבדה.\n"
            "- מודל סטטיסטי על עבר יכול להיראות חיובי אם הגרף חזק — **מסוכן** להתעלם מהדוח.\n",
            "**סדר עבודה**\n\n"
            "- קודם: תזרים, תמחור, פורנזיקה.\n"
            "- אחר כך: מה המודל אומר.\n",
            "- מסך לימוד בלבד — לא המלצת כניסה.\n",
        ]
        out.extend(fusion_parts)
        return out

    if (
        mos is not None
        and mos < -10
        and roic is not None
        and wacc is not None
        and roic < wacc
    ):
        out = [
            "**ניתוח חוקר**\n\n"
            "- מתח בין מחיר השוק לבין ערך במודל.\n"
            "- רווח אחרי עלות הון נראה חלש.\n",
            "**אפשרויות**\n\n"
            "- לא בהכרח הזדמנות.\n"
            "- לפעמים מלכודת ערך.\n",
            "**המשך**\n\n"
            "- תזרים, הכנסות, חוב, דיווח.\n"
            "- רק אז תחזית מחיר כמידע נוסף.\n",
        ]
        out.extend(fusion_parts)
        return out

    out = [
        "**ניתוח חוקר**\n\n"
        "- מניות יקרות יחסית לרווח.\n"
        "- או מניות שמסתמכות על סיפור צמיחה.\n"
        "- אז מדדי \"ערך קלאסי\" לפעמים נראים רע — גם כשהעסק בסדר.\n",
        "**למה?**\n\n"
        f"- צמיחה ו־{C('NRR')} לא תמיד נכנסים ל־{C('P/E')} בצורה נוחה.\n",
        "**שלושה צירים**\n\n"
        "1. צמיחה תפעולית — ביקוש והכנסות.\n"
        "2. מאזן וסיכון — חוב, נזילות, שקיפות דיווח.\n"
        "3. מחיר מול הסיפור.\n",
        "**תחזית סטטיסטית**\n\n"
        "- עוזרת רק אחרי שהצירים ברורים.\n"
        "- פנדמנטלים חלשים — הגרף לא מתקן.\n",
    ]
    out.extend(fusion_parts)
    return out


def render_research_insights_he(
    *,
    dash: dict[str, Any],
    verdict: dict[str, Any] | None,
    study_financials: dict[str, Any] | None = None,
    include_forensic_duplicates: bool = True,
) -> None:
    """Streamlit: flags + expert box (HTML fragments from :func:`md_code`)."""
    import streamlit as st

    lines = build_red_flag_lines_he(
        dash=dash,
        verdict=verdict,
        study_financials=study_financials,
        include_forensic_duplicates=include_forensic_duplicates,
    )
    expert_parts = build_expert_analysis_paragraphs_he(dash=dash, verdict=verdict)

    render_focus_heading("🚩 נורות אזהרה — מה החוקר מדגיש כאן", variant="caution")
    st.caption(
        "מונחים באנגלית, מספרים ונוסחאות מוצגים ב־"
        + C("LTR code")
        + " כדי לשמור כיוון קריא. מידע מורכב מחולק לנקודות.",
        unsafe_allow_html=True,
    )
    if lines:
        for raw in lines:
            for chunk in [c.strip() for c in raw.split("\n\n") if c.strip()]:
                render_focus_block(chunk, variant="caution")
    else:
        st.info("לא נבנו כאן נקודות אזהרה אוטומטיות נוספות מעבר לטבלאות למעלה — עדיין כדאי לבדוק תזרים וחוב ידנית.")

    render_focus_heading("🎓 ניתוח חוקר (איך לקרוא את השילוב)", variant="insight")
    render_focus_block("\n\n".join(expert_parts), variant="insight")
