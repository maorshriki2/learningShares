from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_intel.modules.portfolio.quiz_engine import QuizEngine
from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.chart_snapshot_narrative import render_portfolio_alpha_snapshot
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.mentor_expander import MENTOR_PORTFOLIO, render_mentor
from market_intel.ui.components.portfolio_panel import render_portfolio
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="תיק נייר וחידונים", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("portfolio_quiz")

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("💼 תיק נייר מגרש האימונים — Paper Portfolio & Quizzes")
render_mentor(MENTOR_PORTFOLIO)
render_glossary_terms(["P/E", "WACC"])
st.session_state["guided_symbol"] = str(st.session_state.get("guided_symbol") or "AAPL").strip().upper()
section_divider()

if "quiz_engine" not in st.session_state:
    st.session_state.quiz_engine = QuizEngine()

try:
    snap = client.portfolio()
except Exception as exc:
    st.error(f"שגיאת API: {exc}")
    st.stop()

render_portfolio(snap)

section_divider()
st.subheader("📊 ביצועים מול S&P 500 (Alpha)")

col_alpha, col_bench = st.columns([2, 1])
start_value = col_bench.number_input("ערך התיק בפתיחה ($)", value=100_000.0, step=1000.0)
benchmark = col_bench.selectbox("מדד ייחוס", ["SPY", "QQQ", "IWM", "VOO"], index=0)

if st.button("🔄 טען השוואה"):
    try:
        alpha_resp = client._client.get(
            "/api/v1/portfolio/alpha",
            params={"start_value": start_value, "benchmark": benchmark},
        )
        alpha_resp.raise_for_status()
        alpha = alpha_resp.json()
        st.session_state.alpha_data = alpha
    except Exception as exc:
        st.error(str(exc))

alpha_data: dict[str, Any] | None = st.session_state.get("alpha_data")
with col_alpha:
    if alpha_data:
        portfolio_ret = alpha_data.get("portfolio_total_return_pct", 0)
        spy_ret = alpha_data.get("spy_total_return_pct", 0)
        alpha_val = alpha_data.get("alpha_pct", 0)

        c1, c2, c3 = st.columns(3)
        c1.markdown(
            f"<div class='mi-card'><div class='mi-card-header'>ביצועי התיק</div>"
            f"<div class='mi-card-value' style='color:{'#34d399' if portfolio_ret >= 0 else '#f87171'}'>{portfolio_ret:+.1f}%</div></div>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<div class='mi-card'><div class='mi-card-header'>S&P 500 ({benchmark})</div>"
            f"<div class='mi-card-value' style='color:{'#34d399' if spy_ret >= 0 else '#f87171'}'>{spy_ret:+.1f}%</div></div>",
            unsafe_allow_html=True,
        )
        c3.markdown(
            f"<div class='mi-card'><div class='mi-card-header'>Alpha (עודף)</div>"
            f"<div class='mi-card-value' style='color:{'#34d399' if alpha_val >= 0 else '#f87171'}'>{alpha_val:+.1f}%</div>"
            f"<div class='mi-card-sub'>{'מכה את השוק ✅' if alpha_val > 0 else 'מפגר אחרי השוק ❌'}</div></div>",
            unsafe_allow_html=True,
        )

        spy_dates = alpha_data.get("spy_dates", [])
        spy_vals = alpha_data.get("spy_normalized_values", [])
        if spy_dates and spy_vals:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=spy_dates,
                    y=spy_vals,
                    name=f"{benchmark} (מנורמל)",
                    line=dict(color="#f97316", width=1.5, dash="dot"),
                )
            )
            current_equity = float(snap.get("total_equity", start_value))
            fig.add_trace(
                go.Scatter(
                    x=[spy_dates[0], spy_dates[-1]],
                    y=[start_value, current_equity],
                    name="תיק שלך",
                    line=dict(color="#34d399", width=2.5),
                    mode="lines+markers",
                )
            )
            fig.update_layout(
                template="plotly_dark",
                height=280,
                margin=dict(l=30, r=10, t=20, b=30),
                legend_orientation="h",
                xaxis_title="תאריך",
                yaxis_title="שווי ($)",
            )
            st.plotly_chart(fig, use_container_width=True, width="stretch")
            render_chart_reading_guide("portfolio_alpha_chart")
            render_portfolio_alpha_snapshot(alpha_data, snap, float(start_value), str(benchmark))

        if alpha_data.get("outperforming"):
            st.success("🏆 התיק שלך מכה את השוק! המטרה של כל משקיע אקטיבי.")
        else:
            st.info("💡 כרגע התיק מפגר אחרי המדד. שקול אם הניתוח שלך נכון, או אם תעודת סל פשוטה עדיפה.")
    else:
        st.caption("לחץ 'טען השוואה' לראות Alpha מול המדד.")

section_divider()
st.subheader("🛒 ביצוע עסקאות")
c1, c2, c3 = st.columns(3)
sym = c1.text_input("טיקר", value="AAPL").upper()
qty = c2.number_input("כמות", min_value=0.0001, value=1.0, step=0.1)
px = c3.number_input("מחיר ($)", min_value=0.01, value=200.0, step=0.5)
b1, b2, b3 = st.columns(3)
if b1.button("📗 קנייה"):
    try:
        snap = client.buy(sym, float(qty), float(px))
        st.success(f"✅ קנייה בוצעה: {qty} מניות {sym} ב-${px:.2f}")
        render_portfolio(snap)
        st.session_state.pop("alpha_data", None)
    except Exception as exc:
        st.error(str(exc))
if b2.button("📕 מכירה"):
    try:
        snap = client.sell(sym, float(qty), float(px))
        st.success(f"✅ מכירה בוצעה: {qty} מניות {sym} ב-${px:.2f}")
        render_portfolio(snap)
        st.session_state.pop("alpha_data", None)
    except Exception as exc:
        st.error(str(exc))
if b3.button("🔄 איפוס תיק", type="secondary"):
    try:
        snap = client.reset_portfolio()
        st.warning("התיק אופס. יתרה: $100,000 מזומן.")
        render_portfolio(snap)
        st.session_state.pop("alpha_data", None)
    except Exception as exc:
        st.error(str(exc))

section_divider()
st.subheader("🧠 חידוני Active Recall")

ctx_tab, general_tab = st.tabs(["💼 מבוסס תיק אישי", "📚 שאלות כלליות"])

with ctx_tab:
    st.caption("שאלות שנוצרו בהתאם למניות שיש לך בתיק.")
    if st.button("🔍 טען שאלות מבוססות תיק"):
        try:
            qz_resp = client._client.get("/api/v1/portfolio/contextual-quiz")
            qz_resp.raise_for_status()
            ctx_qs = qz_resp.json().get("questions", [])
            st.session_state.ctx_questions = ctx_qs
            st.session_state.ctx_idx = 0
        except Exception as exc:
            st.error(str(exc))

    ctx_qs: list[dict[str, Any]] = st.session_state.get("ctx_questions", [])
    if not ctx_qs:
        st.info("אין שאלות כרגע — הוסף מניות לתיק ולחץ 'טען'.")
    else:
        idx: int = st.session_state.get("ctx_idx", 0)
        if idx < len(ctx_qs):
            q = ctx_qs[idx]
            st.markdown(f"**שאלה {idx + 1}/{len(ctx_qs)}: {q['prompt']}**")
            choice = st.radio("בחר תשובה:", list(range(len(q["choices"]))), format_func=lambda i: q["choices"][i], key=f"ctx_q_{idx}")
            if st.button("✅ שלח תשובה", key=f"ctx_submit_{idx}"):
                correct = choice == q["correct_index"]
                if correct:
                    st.success("✅ נכון!")
                else:
                    st.error(f"❌ לא נכון. התשובה הנכונה: {q['choices'][q['correct_index']]}")
                st.info(q.get("explanation", ""))
                st.session_state.ctx_idx = idx + 1
        else:
            st.success(f"🎉 סיימת את כל {len(ctx_qs)} השאלות המבוססות תיק!")
            if st.button("🔄 אפס שאלות"):
                st.session_state.ctx_questions = []
                st.session_state.ctx_idx = 0

with general_tab:
    tag = st.selectbox("נושא:", ["mixed", "valuation", "dcf", "governance", "technical"])
    if st.button("🎲 משוך שאלה"):
        tag_val = None if tag == "mixed" else tag
        st.session_state.quiz_engine.next_question(tag_val)

    q = st.session_state.quiz_engine.last_question
    if q:
        st.markdown(f"**{q.prompt}**")
        choice = st.radio("בחר:", list(range(len(q.choices))), format_func=lambda i: q.choices[i], key="gen_q")
        if st.button("✅ שלח", key="gen_submit"):
            ok, expl = st.session_state.quiz_engine.answer(int(choice))
            if ok:
                st.success("✅ נכון!")
            else:
                st.error(f"❌ שגוי. תשובה נכונה: {q.choices[q.correct_index]}")
            st.info(expl)
        st.caption(f"ניקוד: {st.session_state.quiz_engine.score}/{st.session_state.quiz_engine.attempts}")
