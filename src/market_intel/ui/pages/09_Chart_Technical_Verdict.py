from __future__ import annotations

from typing import Any

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.chart_plotly import build_candlestick_figure
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.chart_snapshot_narrative import render_ohlcv_snapshot_narrative
from market_intel.ui.components.chart_verdict_panel import (
    render_chart_technical_verdict_panel,
)
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.state.session import ensure_api_base
from market_intel.ui.state.analysis_cache import require_cached

st.set_page_config(page_title="Chart Technical Verdict", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("chart_technical_verdict")

base = ensure_api_base()

st.title("📊 Chart Technical Verdict — ניתוח מקיף מהגרף בלבד")
st.caption(
    "אותו מקור נתונים כמו מעבדת הגרפים (OHLCV + אינדיקטורים), אבל במסך של "
    "“פסק דין” מובנה — בלי פונדמנטלים. חינוכי בלבד."
)
section_divider()

symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"
artifact = require_cached(
    symbol,
    base,
    "analysis_artifact:v1",
    message_he="אין Artifact שמור. לחץ **ניתוח** בסיידבר כדי לטעון (ברירת מחדל: 1d, 320).",
)
meta = artifact.get("meta") if isinstance(artifact, dict) else {}
cfg = meta.get("config") if isinstance(meta, dict) else {}
tf = str(cfg.get("timeframe") or "1d")
limit = int(cfg.get("limit") or 320)
inputs = artifact.get("inputs") if isinstance(artifact, dict) else {}
payload = inputs.get("ohlcv") if isinstance(inputs, dict) else {}
verdicts = artifact.get("verdicts") if isinstance(artifact, dict) else {}
chart_v = verdicts.get("chart_technical_verdict") if isinstance(verdicts, dict) else {}

candles = payload.get("candles") or []
indicators = payload.get("indicators") or {}
patterns = payload.get("patterns") or []
fib = payload.get("fibonacci")
fib_d = fib if isinstance(fib, dict) else None

@st.cache_data(show_spinner=False, ttl=6 * 60 * 60)
def _fig_cached(
    candles: list[dict[str, Any]],
    indicators: dict[str, Any],
    patterns: list[dict[str, Any]],
):
    return build_candlestick_figure(candles, indicators, patterns)

snapshot = chart_v.get("snapshot") if isinstance(chart_v, dict) else None
if not isinstance(snapshot, dict):
    st.info("אין Chart Technical Verdict בתוך ה־Artifact.")
    st.stop()
render_chart_technical_verdict_panel(snapshot)

section_divider()
st.subheader("גרף מלא לאימות ויזואלית")
fig = _fig_cached(candles, indicators, patterns)
st.plotly_chart(fig, use_container_width=True, width="stretch")

render_chart_reading_guide(
    "chart_technical_verdict",
    expander_title="📖 איך לקרוא את פסק הדין הטכני (גרף בלבד)",
)

section_divider()
st.subheader("נרטיב מפורט מהנרות (אותו מנוע כמו Charting Lab)")
render_ohlcv_snapshot_narrative(
    symbol=symbol,
    timeframe=tf,
    candles=candles,
    indicators=indicators,
    patterns=patterns,
    fibonacci=fib_d,
)

st.caption("Educational only — not investment advice.")
