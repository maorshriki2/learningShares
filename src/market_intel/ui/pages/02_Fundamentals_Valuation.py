from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from market_intel.modules.fundamentals.education.dcf_explainer import margin_of_safety_note
from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.active_recall import render_active_recall_checkpoint
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.dcf_sliders import dcf_controls
from market_intel.ui.components.financial_snapshot_narrative import (
    render_forensic_analyst_alerts,
    render_fundamentals_snapshot,
)
from market_intel.ui.components.fundamentals_tables import statements_tabs
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.guided_learning import render_guided_learning_sidebar
from market_intel.ui.components.mentor_expander import MENTOR_FUNDAMENTALS, render_mentor
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="Fundamentals", layout="wide")
inject_terminal_theme()
inject_card_css()

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("📋 Fundamentals & Valuation — ניתוח פונדמנטלי")
render_mentor(MENTOR_FUNDAMENTALS)
render_glossary_terms(["P/E", "ROIC", "Altman Z", "WACC"])
section_divider()
symbol = st.text_input(
    "Symbol",
    value=st.session_state.get("guided_symbol", "AAPL"),
).strip().upper()
symbol = render_guided_learning_sidebar("fundamentals", symbol, show_symbol_input=False)

try:
    dash = client.fundamentals_dashboard(symbol, years=10)
except Exception as exc:
    st.error(f"API error: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("WACC (model)", f"{float(dash.get('wacc', 0))*100:.2f}%")
if dash.get("roic_latest") is not None:
    c2.metric("ROIC (latest)", f"{float(dash['roic_latest'])*100:.2f}%")
else:
    c2.metric("ROIC (latest)", "n/a")
_piot = dash.get("piotroski_score")
c3.metric("Piotroski F", str(_piot) if _piot is not None else "n/a")
_az = dash.get("altman_z")
c4.metric("Altman Z", f"{float(_az):.2f}" if _az is not None else "n/a")

render_forensic_analyst_alerts(dash)

render_chart_reading_guide(
    "fundamentals_kpis_dcf",
    expander_title="📖 איך לקרוא את המדדים, ה־WACC וה־DCF",
)
render_fundamentals_snapshot(dash)

sens = dash.get("dcf_sensitivity")
if isinstance(sens, dict) and sens.get("intrinsic_per_share_matrix"):
    st.subheader("🧮 מטריצת רגישות DCF (Stress Test)")
    st.caption(
        "מחיר הוגן למניה לפי מודל DCF פנימי. **WACC** בטווח ±2 נק׳ אחוז; "
        "**צמיחה טרמינלית** בטווח ±1 נק׳ אחוז. "
        "צבעים: ירוק = שווי מודל גבוה יותר; אדום = נמוך יותר."
    )
    zmat = sens["intrinsic_per_share_matrix"]
    w_axis = sens.get("wacc_values") or []
    t_axis = sens.get("terminal_growth_values") or []
    x_labels = [f"{float(t) * 100:.2f}%" for t in t_axis]
    y_labels = [f"{float(w) * 100:.2f}%" for w in w_axis]
    z_num: list[list[float | None]] = []
    text_m: list[list[str]] = []
    for row in zmat:
        zr: list[float | None] = []
        tr: list[str] = []
        for cell in row:
            if cell is None:
                zr.append(float("nan"))
                tr.append("—")
            else:
                fv = float(cell)
                zr.append(fv)
                tr.append(f"{fv:.1f}")
        z_num.append(zr)
        text_m.append(tr)
    mp = dash.get("market_price")
    zmid_val = None
    if mp is not None and isinstance(mp, (int, float)) and math.isfinite(float(mp)):
        zmid_val = float(mp)
    fig_h = go.Figure(
        data=go.Heatmap(
            z=z_num,
            x=x_labels,
            y=y_labels,
            text=text_m,
            texttemplate="%{text}",
            colorscale="RdYlGn",
            zmid=zmid_val,
            colorbar=dict(title="$/מניה"),
        )
    )
    fig_h.update_layout(
        template="plotly_dark",
        height=420,
        xaxis_title="Terminal growth (טור)",
        yaxis_title="WACC (שורה)",
        margin=dict(l=60, r=20, t=40, b=60),
    )
    if mp is not None and math.isfinite(float(mp)):
        mps = float(mp)
        st.caption(
            f"מחיר שוק נוכחי (השוואה): **{mps:.2f}** — "
            "תאים עם שווי מודל גבוה ממנו: לרוב «זול יחסית למודל»; נמוך ממנו: «יקר יחסית»."
        )
    st.plotly_chart(fig_h, width="stretch")

st.subheader("Statements (SEC XBRL company facts)")
statements_tabs(dash)
render_chart_reading_guide(
    "fundamentals_statements",
    expander_title="📖 איך לקרוא את דוחות ה־Income / Balance / Cash Flow",
)

st.subheader("Interactive DCF")
growth, terminal, wacc = dcf_controls()
if st.button("Recompute DCF scenario"):
    try:
        scenario = client.dcf_scenario(symbol, growth, terminal, wacc)
        st.success(scenario.get("summary", ""))
        st.write(
            {
                "enterprise_value": scenario.get("enterprise_value"),
                "intrinsic_per_share": scenario.get("intrinsic_per_share"),
            }
        )
        st.info(scenario.get("margin_of_safety_note", margin_of_safety_note()))
    except Exception as exc:
        st.error(str(exc))

with st.expander("Margin of safety (tooltip-style note)"):
    st.write(margin_of_safety_note())

section_divider()
render_active_recall_checkpoint(
    page_key="fundamentals",
    prompt="איזה ערך Altman Z נחשב לרוב אזור סכנה?",
    choices=["מעל 3.0", "בין 2.0 ל-3.0", "מתחת ל-1.81", "מעל 10"],
    correct_index=2,
    explanation="Altman Z מתחת ל-1.81 מזוהה לרוב כאזור סיכון גבוה למצוקה פיננסית.",
)
