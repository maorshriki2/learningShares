from __future__ import annotations

from typing import Any

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.blind_case_display import render_blind_case_metrics_and_chart
from market_intel.ui.components.blind_csv_io import blind_study_to_csv_bytes
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.mentor_expander import MENTOR_BLIND_TEST, render_mentor
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="מבחן עיוור", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("blind_test")

base = ensure_api_base()
client = MarketIntelApiClient(base)


def _load_random() -> dict[str, Any]:
    r = client._client.get("/api/v1/blindtest/random")
    r.raise_for_status()
    return r.json()


def _load_study(sid: str) -> dict[str, Any]:
    r = client._client.get(f"/api/v1/blindtest/{sid}/blind")
    r.raise_for_status()
    return r.json()


def _post_reveal(sid: str, decision: str, explanation: str) -> dict[str, Any]:
    r = client._client.post(
        f"/api/v1/blindtest/{sid}/reveal",
        json={"decision": decision, "explanation": explanation},
    )
    r.raise_for_status()
    return r.json()


st.title("🕵️ מבחן עיוור — Blind Test Case Studies")
render_mentor(MENTOR_BLIND_TEST)
render_glossary_terms(["P/E", "Altman Z"])
st.session_state["guided_symbol"] = str(st.session_state.get("guided_symbol") or "AAPL").strip().upper()
section_divider()

if "bt_study" not in st.session_state:
    st.session_state.bt_study = None
    st.session_state.bt_revealed = False
    st.session_state.bt_decision = None
    st.session_state.bt_explanation = ""
    st.session_state.bt_reveal_data = None

col_load, col_list = st.columns([1, 2])
if col_load.button("🎲 טען מקרה אקראי", type="primary"):
    try:
        st.session_state.bt_study = _load_random()
        st.session_state.bt_revealed = False
        st.session_state.bt_decision = None
        st.session_state.bt_reveal_data = None
    except Exception as exc:
        st.error(f"שגיאה: {exc}")

try:
    ids_resp = client._client.get("/api/v1/blindtest/list")
    ids_resp.raise_for_status()
    all_ids = ids_resp.json().get("ids", [])
except Exception:
    all_ids = []

selected_id = col_list.selectbox("— או בחר מקרה ספציפי:", ["(ללא)"] + all_ids, index=0)
if selected_id != "(ללא)" and st.session_state.bt_study and st.session_state.bt_study.get("id") != selected_id:
    try:
        st.session_state.bt_study = _load_study(selected_id)
        st.session_state.bt_revealed = False
        st.session_state.bt_decision = None
        st.session_state.bt_reveal_data = None
    except Exception as exc:
        st.error(str(exc))

study: dict[str, Any] | None = st.session_state.bt_study
if study is None:
    st.info("לחץ על 'טען מקרה אקראי' כדי להתחיל.")
    st.stop()

section_divider()
render_blind_case_metrics_and_chart(study, company_label=study["codename"], show_codename_in_title=True)

section_divider()
st.markdown("#### ייצוא")
st.caption("שמור את אותה סיטואציה לקובץ CSV — לטעינה במסך **Blind CSV** עם שם אנונימי קבוע (`anony`).")
csv_bytes = blind_study_to_csv_bytes(study)
st.download_button(
    label="📥 ייצא את הסיטואציה לקובץ CSV",
    data=csv_bytes,
    file_name=f"blind_case_{study.get('id', 'case')}.csv",
    mime="text/csv",
    help="שורה אחת: נתונים פיננסיים + price_chart_json. בלי שם החברה האמיתי.",
)

section_divider()
if not st.session_state.bt_revealed:
    st.markdown("### 🎯 קבל החלטה")
    decision = st.radio(
        "ההמלצה שלך:",
        ["קנייה חזקה", "המתנה", "שורט (מכירה בחסר)"],
        horizontal=True,
    )
    explanation = st.text_area("הסבר בקצרה את ההיגיון שלך:", height=80)
    if st.button("🔍 חשיפה — גלה מי החברה!", type="primary"):
        if not explanation.strip():
            st.warning("כתוב לפחות משפט הסבר לפני החשיפה.")
        else:
            try:
                reveal = _post_reveal(study["id"], decision, explanation)
                st.session_state.bt_reveal_data = reveal
                st.session_state.bt_decision = decision
                st.session_state.bt_revealed = True
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

if st.session_state.bt_revealed and st.session_state.bt_reveal_data:
    rev = st.session_state.bt_reveal_data
    section_divider()
    st.markdown(f"## 🎉 חשיפה: **{rev['reveal_name']}**")
    st.markdown(f"**תוצאה:** {rev['outcome_label']}")

    c_g, c_p = st.columns(2)
    ret = rev.get("actual_return_pct", 0)
    ret_color = "green" if ret >= 0 else "red"
    c_g.markdown(
        f"<div class='mi-card'><div class='mi-card-header'>תשואה בשנה שלאחר מכן</div>"
        f"<div class='mi-card-value' style='color:{'#34d399' if ret >= 0 else '#f87171'}'>{ret:+.1f}%</div></div>",
        unsafe_allow_html=True,
    )
    correct = rev.get("decision_correct", False)
    c_p.markdown(
        f"<div class='mi-card'><div class='mi-card-header'>הציון שלך</div>"
        f"<div class='mi-card-value' style='color:{'#34d399' if correct else '#f87171'}'>"
        f"{'✅ נכון' if correct else '❌ שגוי'}</div></div>",
        unsafe_allow_html=True,
    )
    st.info(rev.get("grade_explanation", ""))
    section_divider()

    red_flags = rev.get("red_flags", [])
    if red_flags:
        st.markdown("### 🚩 נורות האזהרה שהיית צריך לזהות:")
        for flag in red_flags:
            st.error(f"• {flag}")

    st.markdown("### 🎓 ניתוח מומחה:")
    st.success(rev.get("expert_analysis", ""))

    if st.button("🔄 מקרה חדש"):
        st.session_state.bt_study = None
        st.session_state.bt_revealed = False
        st.session_state.bt_decision = None
        st.session_state.bt_reveal_data = None
        st.rerun()
