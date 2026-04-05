from __future__ import annotations

import streamlit as st

TERM_DEFINITIONS_HE: dict[str, str] = {
    "P/E": "מכפיל רווח: מחיר המניה חלקי הרווח למניה. גבוה = ציפיות צמיחה גבוהות.",
    "ROIC": "תשואה על ההון המושקע: כמה יעילה החברה בייצור רווח מההון.",
    "MACD": "אינדיקטור מומנטום מבוסס ממוצעים נעים. חציה מעל קו האיתות עשויה להיות שורית.",
    "VWAP": "מחיר ממוצע משוקלל נפח. משמש להערכת מחיר הוגן תוך יומי.",
    "Altman Z": "ציון סיכון פיננסי/פשיטת רגל. נמוך מ-1.81 נחשב אזור סכנה.",
    "WACC": "עלות הון ממוצעת משוקללת. ככל שהיא גבוהה יותר, שווי DCF לרוב יורד.",
    "EV/EBITDA": "מכפיל תפעולי לנטרול מבנה הון. נמוך יחסית עשוי לרמוז על תמחור נוח.",
}


def render_glossary_terms(terms: list[str]) -> None:
    parts: list[str] = []
    for term in terms:
        explanation = TERM_DEFINITIONS_HE.get(term)
        if not explanation:
            continue
        parts.append(
            f'<span title="{explanation}" style="padding:4px 8px;border:1px solid #334155;'
            f'border-radius:999px;margin-left:6px;display:inline-block;">{term}</span>'
        )
    if parts:
        st.markdown("**מילון מרחף (רחף עם העכבר):**", help="הסבר קצר מיידי למונחים מקצועיים")
        st.markdown(" ".join(parts), unsafe_allow_html=True)
