from __future__ import annotations

import math
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, metric_card, section_divider
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.chart_snapshot_narrative import (
    render_treasury_history_snapshot,
)
from market_intel.ui.components.mentor_expander import MENTOR_MACRO, render_mentor
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="מאקרו וריבית", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("macro_sim")

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("🏦 מאקרו כלכלה וסימולטור ריבית — Macro & WACC")
render_mentor(MENTOR_MACRO)
render_glossary_terms(["WACC"])
section_divider()
st.session_state["guided_symbol"] = str(st.session_state.get("guided_symbol") or "AAPL").strip().upper()

try:
    rates: dict[str, Any] = client.macro_rates()
except Exception as exc:
    st.error(f"שגיאה בטעינת ריביות FRED: {exc}")
    st.info("בדוק שהאפליקציה רצה: `python scripts/run_app.py` (API + ממשק יחד).")
    rates = {"treasury_10y": 4.35, "treasury_2y": 4.90, "fed_funds": 5.33}

c1, c2, c3 = st.columns(3)
t10 = rates.get("treasury_10y", 4.35)
t2 = rates.get("treasury_2y", 4.90)
ff = rates.get("fed_funds", 5.33)
with c1:
    metric_card("אג\"ח ל-10 שנים", f"{t10:.2f}%", "Risk-Free Rate", badge="ריבית עדכנית", badge_color="blue")
with c2:
    metric_card("אג\"ח ל-2 שנים", f"{t2:.2f}%", "Short Term", badge_color="yellow")
with c3:
    inv = t2 > t10
    metric_card("Fed Funds Rate", f"{ff:.2f}%", "ריבית פד", badge="עקום הפוך ⚠️" if inv else "רגיל", badge_color="red" if inv else "green")

if inv:
    st.warning("⚠️ **עקום תשואות הפוך**: ריבית 2 שנים גבוהה מ-10 שנים — היסטורית קשורה להאטה כלכלית.")

try:
    hist_data = client.macro_rate_history(series="DGS10", limit=104).get("data", [])
except Exception:
    hist_data = []

if hist_data:
    df_hist = pd.DataFrame(hist_data)
    df_hist["date"] = pd.to_datetime(df_hist["date"])
    fig_hist = px.line(
        df_hist,
        x="date",
        y="value",
        title="תשואת אג\"ח ל-10 שנים — 2 שנות עבר",
        labels={"date": "תאריך", "value": "תשואה (%)"},
        template="plotly_dark",
        color_discrete_sequence=["#38bdf8"],
    )
    fig_hist.update_layout(height=280, margin=dict(l=30, r=10, t=40, b=30))
    st.plotly_chart(fig_hist, use_container_width=True, width="stretch")
    render_chart_reading_guide("macro_treasury_history")
    vals = [float(v) for v in df_hist["value"].tolist() if v == v]
    render_treasury_history_snapshot(vals)

section_divider()
st.markdown("### 🎛️ סימולטור — מה יקרה אם הריבית תשתנה?")
st.caption("שנה את הפרמטרים, הזז את הסליידר, וראה איך שווי החברה משתנה.")

col_a, col_b = st.columns(2)
with col_a:
    rfr = st.slider("ריבית חסרת סיכון נוכחית (%)", 0.0, 12.0, float(t10), 0.05, help="שינה לריבית נוכחית מ-FRED")
    beta = st.slider("בטא (רגישות לשוק)", 0.3, 3.0, 1.2, 0.05)
    erp = st.slider("פרמיית סיכון שוק — ERP (%)", 2.0, 10.0, 5.5, 0.1)
    growth = st.slider("צמיחת FCF שנות 1–5 (%)", -5.0, 40.0, 10.0, 0.5)
    terminal = st.slider("צמיחה טרמינלית (%)", 0.0, 5.0, 2.0, 0.1)
with col_b:
    base_fcf = st.number_input("FCF בסיסי ($M)", min_value=1.0, value=5000.0, step=100.0)
    shares = st.number_input("מניות בסחר (M) — 0 לחישוב EV בלבד", min_value=0.0, value=0.0, step=50.0)
    net_debt = st.number_input("חוב נטו ($M)", value=0.0, step=100.0)
    eq_w = st.slider("משקל הון עצמי (%)", 10, 100, 80, 5) / 100.0
    tax = st.slider("שיעור מס (%)", 5.0, 40.0, 21.0, 0.5) / 100.0

rate_range = st.slider("טווח שינוי ריבית (נקודות אחוז)", -4.0, 4.0, (-3.0, 3.0), 0.5)

if st.button("🚀 הרץ סימולציה", type="primary"):
    payload = {
        "current_risk_free": rfr / 100.0,
        "equity_risk_premium": erp / 100.0,
        "beta": beta,
        "cost_of_debt_pretax": 0.05,
        "tax_rate": tax,
        "equity_weight": eq_w,
        "debt_weight": 1.0 - eq_w,
        "base_fcf": base_fcf * 1_000_000,
        "growth": growth / 100.0,
        "terminal_growth": terminal / 100.0,
        "shares_outstanding": float(shares * 1_000_000) if shares > 0 else None,
        "net_debt": net_debt * 1_000_000,
        "rate_delta_from": float(rate_range[0]),
        "rate_delta_to": float(rate_range[1]),
        "rate_delta_step": 0.5,
    }
    try:
        sim = client.macro_wacc_simulation(payload)
    except Exception as exc:
        st.error(f"שגיאת סימולציה: {exc}")
        st.stop()

    scenarios = sim.get("scenarios", [])
    base_wacc = sim.get("base_wacc_pct", 0)
    st.success(f"WACC בסיסי (ריבית נוכחית): **{base_wacc:.2f}%**")
    df_sim = pd.DataFrame(scenarios)

    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=df_sim["rate_delta_pct"],
            y=df_sim["ev_change_pct"],
            mode="lines+markers",
            name="שינוי שווי (%)",
            line=dict(color="#34d399", width=2.5),
            hovertemplate="שינוי ריבית: %{x:+.1f}%<br>שינוי שווי: %{y:.1f}%",
        )
    )
    fig1.add_vline(x=0, line_dash="dash", line_color="rgba(148,163,184,0.4)")
    fig1.update_layout(
        title="השפעת שינוי ריבית על שווי החברה (EV)",
        xaxis_title="שינוי ריבית (pp)",
        yaxis_title="שינוי שווי (%)",
        template="plotly_dark",
        height=340,
        margin=dict(l=40, r=20, t=40, b=30),
    )
    st.plotly_chart(fig1, use_container_width=True, width="stretch")

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=df_sim["rate_delta_pct"],
            y=df_sim["wacc"],
            mode="lines+markers",
            name="WACC (%)",
            line=dict(color="#f97316", width=2),
        )
    )
    fig2.update_layout(
        title="WACC לפי שינוי ריבית",
        xaxis_title="שינוי ריבית (pp)",
        yaxis_title="WACC (%)",
        template="plotly_dark",
        height=260,
        margin=dict(l=40, r=20, t=40, b=30),
    )
    st.plotly_chart(fig2, use_container_width=True, width="stretch")
    render_chart_reading_guide("macro_wacc_simulation")

    if shares > 0:
        df_share = df_sim[df_sim["implied_per_share"].notnull()]
        if not df_share.empty:
            st.dataframe(
                df_share[["rate_delta_pct", "risk_free_rate", "wacc", "implied_per_share"]].rename(
                    columns={
                        "rate_delta_pct": "שינוי ריבית (pp)",
                        "risk_free_rate": "ריבית חסרת סיכון (%)",
                        "wacc": "WACC (%)",
                        "implied_per_share": "מחיר הוגן ($)",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

