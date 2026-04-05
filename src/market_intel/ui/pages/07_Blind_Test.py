from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.active_recall import render_active_recall_checkpoint
from market_intel.ui.components.cards import inject_card_css, metric_card, section_divider, signal_color
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.chart_snapshot_narrative import render_blind_price_snapshot
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.guided_learning import render_guided_learning_sidebar
from market_intel.ui.components.mentor_expander import MENTOR_BLIND_TEST, render_mentor
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="מבחן עיוור", layout="wide")
inject_terminal_theme()
inject_card_css()

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
render_guided_learning_sidebar("blind_test", st.session_state.get("guided_symbol", "AAPL"), show_symbol_input=False)
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
st.markdown(f"## חברה: **{study['codename']}** | שנה: {study['year']} | סקטור: {study['sector']}")
st.caption(f"מחיר נקודת ה-snapshot: ${study['price_at_snapshot']:.2f}")

fin = study.get("financials_summary", {})
c1, c2, c3, c4 = st.columns(4)
with c1:
    pe = fin.get("pe_ratio")
    metric_card("P/E", f"{pe:.1f}" if pe else "N/A (הפסד)", badge_color="yellow" if pe else "red")
with c2:
    roa = (fin.get("net_income_b") or 0) / (fin.get("total_assets_b") or 1) * 100
    metric_card("ROA", f"{roa:.1f}%", badge_color=signal_color(roa, 0, 5))
with c3:
    dte = fin.get("debt_to_equity")
    metric_card("חוב/הון (D/E)", f"{dte:.1f}x" if dte else "N/A", badge_color=signal_color(-(dte or 0), -3, -0.5))
with c4:
    ocf = fin.get("operating_cashflow_b")
    metric_card("תזרים תפעולי", f"${ocf:+.1f}B" if ocf is not None else "N/A",
                badge_color="green" if ocf and ocf > 0 else "red")

c5, c6, c7, c8 = st.columns(4)
with c5:
    piotr = study.get("piotroski_score")
    badge_p = "green" if piotr and piotr >= 7 else ("yellow" if piotr and piotr >= 4 else "red")
    metric_card("Piotroski F", f"{piotr}/9" if piotr is not None else "N/A", badge_color=badge_p)
with c6:
    z = study.get("altman_z")
    zone = study.get("altman_zone", "grey")
    z_color = "green" if zone == "safe" else ("red" if zone == "danger" else "yellow")
    metric_card("Altman Z", f"{z:.2f}" if z else "N/A", zone, badge_color=z_color)
with c7:
    rev = fin.get("revenue_b")
    metric_card("הכנסות", f"${rev:.1f}B" if rev else "N/A")
with c8:
    ni = fin.get("net_income_b")
    metric_card("רווח נקי", f"${ni:+.2f}B" if ni is not None else "N/A",
                badge_color="green" if ni and ni > 0 else "red")

section_divider()
st.markdown("### 📈 גרף מחיר (יחסי — בלי תאריכים מזהים)")
chart_data = study.get("price_chart_data", [])
if chart_data:
    price_snap = study["price_at_snapshot"]
    x_labels = [f"t{d['offset_months']:+d}m" for d in chart_data]
    prices = [round(d["price_factor"] * price_snap, 2) for d in chart_data]
    colors = ["#34d399" if p >= price_snap else "#f87171" for p in prices]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=prices,
            mode="lines+markers",
            name="מחיר יחסי",
            line=dict(color="#38bdf8", width=2),
            marker=dict(color=colors, size=9),
        )
    )
    fig.add_hline(y=price_snap, line_dash="dot", line_color="rgba(248,248,248,0.25)", annotation_text="Snapshot")
    fig.update_layout(
        template="plotly_dark",
        height=300,
        margin=dict(l=30, r=20, t=20, b=30),
        xaxis_title="תקופה (t=0 = נקודת snapshot)",
        yaxis_title="מחיר ($)",
    )
    st.plotly_chart(fig, width="stretch")
    render_chart_reading_guide("blind_price_context")
    render_blind_price_snapshot(chart_data, float(price_snap))

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

section_divider()
render_active_recall_checkpoint(
    page_key="blind_test",
    prompt="איזה צירוף הוא Red Flag קלאסי בבדיקה עיוורת?",
    choices=[
        "Altman Z נמוך מ-1.81 ומינוף גבוה",
        "Piotroski גבוה מ-7 ותזרים חיובי",
        "צמיחה יציבה וחוב נמוך",
        "שיפור מתמשך במרג'ין",
    ],
    correct_index=0,
    explanation="Altman Z נמוך יחד עם מינוף גבוה מצביעים לרוב על סיכון מבני ממשי.",
)
