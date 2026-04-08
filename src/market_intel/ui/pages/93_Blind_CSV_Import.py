from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
import streamlit as st

from market_intel.modules.blind_test.case_study_engine import CaseStudyEngine
from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.blind_case_display import render_blind_case_metrics_and_chart
from market_intel.ui.components.blind_csv_io import blind_study_from_csv_bytes
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.financial_snapshot_narrative import (
    render_forensic_analyst_alerts,
    render_fundamentals_snapshot,
)
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.stock360_result_panel import render_stock360_verdict_result
from market_intel.ui.state.session import discover_api_base_with_blind_analyze_route, ensure_api_base

ANONY_NAME = "anony"
_SS_STUDY = "blind_csv_import_study"
_SS_FNAME = "blind_csv_import_filename"
_UPLOADER_KEY = "blind_csv_uploader_widget"
_SS_ANALYSIS = "blind_csv_full_analysis"
_SS_ANALYSIS_FP = "blind_csv_analysis_fingerprint"


def _study_fingerprint(study: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(study, sort_keys=True, default=str).encode()).hexdigest()[:24]


st.set_page_config(page_title="Blind CSV — אנונימי", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("blind_csv")

st.title("📄 Blind Test — ייבוא מתוך CSV (אנונימי)")
st.caption(
    "העלה קובץ CSV שיוצא ממסך Blind Test. השם המוצג תמיד "
    f"**{ANONY_NAME}** — בלי קשר לתוכן הקובץ — כדי לבדוק מודלים/היגיון בלי הטיה של שם."
)
with st.expander("עמודות אופציונליות (ציון אוטומטי)"):
    st.markdown(
        """
הייצוא מהמסך הרגיל **לא** כולל מחיר עתידי (כדי שלא ידלוף „תשובה”). אם תרצה ציון אוטומטי כאן, אפשר להוסיף ידנית ל־CSV עמודות כמו:

- `price_one_year_later` — מחיר כשנה אחרי ה-snapshot  
- `reveal_name`, `outcome_label` — טקסטים להצגה אחרי בדיקה  

בלי `price_one_year_later` — אין בדיקת ציון אוטומטית בתחתית, אבל עדיין אפשר להריץ את **אותו ניתוח מלא** כמו Stock 360.
"""
    )

up = st.file_uploader(
    "קובץ CSV",
    type=["csv"],
    help="פורמט שורה אחת כמו בייצוא מהמסך הקודם. אחרי טעינה המקרה נשמר בזיכרון הסשן עד שתנקה.",
    key=_UPLOADER_KEY,
)

study: dict[str, Any] | None = None
from_session = False

if up is not None:
    try:
        raw = up.getvalue()
        study = blind_study_from_csv_bytes(raw)
        st.session_state[_SS_STUDY] = study
        st.session_state[_SS_FNAME] = up.name
    except Exception as exc:
        st.error(f"לא הצלחנו לקרוא את הקובץ: {exc}")
        study = st.session_state.get(_SS_STUDY)
        if study is None:
            st.stop()
elif _SS_STUDY in st.session_state:
    study = st.session_state[_SS_STUDY]
    from_session = True
else:
    st.info("בחר קובץ CSV כדי לטעון סיטואציה.")
    st.stop()

assert study is not None

fp = _study_fingerprint(study)
if st.session_state.get(_SS_ANALYSIS_FP) != fp:
    st.session_state.pop(_SS_ANALYSIS, None)
    st.session_state[_SS_ANALYSIS_FP] = fp

if from_session:
    fname = st.session_state.get(_SS_FNAME) or "קובץ"
    st.caption(f"📎 מוצג מקרה שמור מהעלאה קודמת (**{fname}**) — נשאר אחרי מעבר בין טאבים.")

c_clear, _ = st.columns([1, 4])
with c_clear:
    if st.button("🗑️ נקה מקרה מהזיכרון"):
        st.session_state.pop(_SS_STUDY, None)
        st.session_state.pop(_SS_FNAME, None)
        st.session_state.pop(_UPLOADER_KEY, None)
        st.session_state.pop(_SS_ANALYSIS, None)
        st.session_state.pop(_SS_ANALYSIS_FP, None)
        st.rerun()

section_divider()
render_blind_case_metrics_and_chart(study, company_label=ANONY_NAME, show_codename_in_title=True)

section_divider()
st.markdown("### 🧠 ניתוח מלא — אותו מנוע כמו Stock 360 (Final Verdict)")
st.caption(
    "השרת מריץ את **אותה ליבה** כמו `/api/v1/stock360/{symbol}/final-verdict`: "
    "אינטרפולציה של גרף המחיר לסדרה יומית, אינדיקטורים, רגרסיה לפי אופקים, והנחות פנדמנטל ממופות מה-CSV."
)
col_run, col_hz = st.columns([1, 2])
with col_hz:
    hz = st.text_input("אופקים (ימים, מופרדים בפסיק)", value="30,90,365")
with col_run:
    st.write("")
    st.write("")
    run_full = st.button("הרץ ניתוח מלא", type="primary")

if run_full:
    base_now = ensure_api_base()
    client = MarketIntelApiClient(base_now)
    try:
        res = client.blind_analyze_scenario(study, horizon_days=hz.strip() or "30,90,365", include_explain=True)
        st.session_state[_SS_ANALYSIS] = res
        st.session_state[_SS_ANALYSIS_FP] = fp
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            found = discover_api_base_with_blind_analyze_route(preferred_base=base_now)
            if found is not None and found != base_now:
                st.session_state.api_base = found
                st.success(
                    f"הפורט הקודם ({base_now}) היה כנראה שרת ישן. נמצא API מעודכן: **{found}** — מנסה שוב."
                )
                try:
                    client2 = MarketIntelApiClient(found)
                    res = client2.blind_analyze_scenario(
                        study, horizon_days=hz.strip() or "30,90,365", include_explain=True
                    )
                    st.session_state[_SS_ANALYSIS] = res
                    st.session_state[_SS_ANALYSIS_FP] = fp
                except Exception as exc2:
                    st.error(f"אחרי מעבר לפורט המעודכן עדיין נכשל: {exc2}")
            else:
                st.error(
                    "**404 — אין נתיב analyze-scenario בשרת שבחרת.** "
                    "לא נמצא API מקומי אחר (8000–8020) עם הנתיב. "
                    "עצור תהליכי Python על הפורט הרלוונטי והפעל `python scripts/run_app.py`, "
                    "או עדכן ב־sidebar את **API base URL** לפורט שבו רץ השרת המעודכן. "
                    f"בקשה: `{exc.request.url}`"
                )
        else:
            st.error(f"שגיאת API ({exc.response.status_code}): {exc}")
    except Exception as exc:
        st.error(f"שגיאת API: {exc}")

analysis = st.session_state.get(_SS_ANALYSIS)
if analysis and isinstance(analysis, dict) and analysis.get("ok"):
    dash_ui = analysis.get("blind_dashboard") or {}
    st.markdown("#### סיכום פנדמנטלי (טבלת Beginner — כמו Fundamentals)")
    render_fundamentals_snapshot(dash_ui)
    render_forensic_analyst_alerts(dash_ui)
    section_divider()
    st.markdown("#### Final Verdict — כיוון / הסתברויות / סיכונים")
    render_stock360_verdict_result(
        analysis,
        include_explain=True,
        study_financials=study.get("financials_summary"),
        research_include_forensic=False,
    )

section_divider()
has_answer_key = "price_one_year_later" in study and study.get("price_at_snapshot", 0) > 0

if not has_answer_key:
    st.warning(
        "בקובץ אין עמודת `price_one_year_later` (מפתח תשובה). "
        "אין ציון אוטומטי מול תוצאה היסטורית — השתמש בניתוח המלא למעלה."
    )
else:
    st.markdown("### 🎯 קבל החלטה (מול מפתח התשובה בקובץ)")
    decision = st.radio(
        "ההמלצה שלך:",
        ["קנייה חזקה", "המתנה", "שורט (מכירה בחסר)"],
        horizontal=True,
    )
    explanation = st.text_area("הסבר בקצרה את ההיגיון שלך:", height=80)

    if st.button("🔍 בדוק מול תוצאה (לפי הקובץ)", type="primary"):
        if not explanation.strip():
            st.warning("כתוב לפחות משפט הסבר.")
        else:
            price_later = float(study["price_one_year_later"])
            price_now = float(study["price_at_snapshot"])
            actual_return_pct = ((price_later - price_now) / price_now * 100) if price_now > 0 else -100.0
            actual_return_pct = round(actual_return_pct, 1)
            decision_correct = CaseStudyEngine._grade(decision, actual_return_pct)
            grade_text = CaseStudyEngine._grade_text(decision, actual_return_pct, decision_correct)

            section_divider()
            reveal_name = study.get("reveal_name") or "—"
            outcome_label = study.get("outcome_label") or "—"
            st.markdown(f"## תוצאה (מפתח מהקובץ): **{reveal_name}**")
            st.markdown(f"**תווית:** {outcome_label}")

            ret = actual_return_pct
            st.markdown(
                f"<div class='mi-card'><div class='mi-card-header'>תשואה בשנה שלאחר ה-snapshot</div>"
                f"<div class='mi-card-value' style='color:{'#34d399' if ret >= 0 else '#f87171'}'>{ret:+.1f}%</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='mi-card'><div class='mi-card-header'>הציון שלך</div>"
                f"<div class='mi-card-value' style='color:{'#34d399' if decision_correct else '#f87171'}'>"
                f"{'✅ נכון' if decision_correct else '❌ שגוי'}</div></div>",
                unsafe_allow_html=True,
            )
            st.info(grade_text)
