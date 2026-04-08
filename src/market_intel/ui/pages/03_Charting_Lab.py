from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.clients.ws_client import MarketIntelWebSocketClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.chart_plotly import build_candlestick_figure
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.chart_snapshot_narrative import render_ohlcv_snapshot_narrative
from market_intel.ui.components.education_sidebar import render_pattern_education
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.mentor_expander import MENTOR_CHARTING, render_mentor
from market_intel.ui.state.session import ensure_api_base
from market_intel.ui.state.analysis_cache import require_cached

st.set_page_config(page_title="Charting Lab", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("charting")

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("📈 Charting Lab — מעבדת גרפים")
render_mentor(MENTOR_CHARTING)
render_glossary_terms(["MACD", "VWAP"])
section_divider()
symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"
artifact = require_cached(
    symbol,
    base,
    "analysis_artifact:v1",
    message_he="אין Artifact שמור לטאב הזה. לחץ **ניתוח** בסיידבר מתחת לסימבול כדי לטעון הכל פעם אחת.",
)
meta = artifact.get("meta") if isinstance(artifact, dict) else {}
cfg = meta.get("config") if isinstance(meta, dict) else {}
tf = str(cfg.get("timeframe") or "1d")
inputs = artifact.get("inputs") if isinstance(artifact, dict) else {}
payload = inputs.get("ohlcv") if isinstance(inputs, dict) else {}

candles = payload.get("candles") or []
indicators = payload.get("indicators") or {}
patterns = payload.get("patterns") or []

@st.cache_data(show_spinner=False, ttl=6 * 60 * 60)
def _candlestick_fig_cached(candles: list[dict[str, Any]], indicators: dict[str, Any], patterns: list[dict[str, Any]]):
    return build_candlestick_figure(candles, indicators, patterns)

fig = _candlestick_fig_cached(candles, indicators, patterns)
st.plotly_chart(fig, use_container_width=True, width="stretch")
render_chart_reading_guide("charting_candles")
fib = payload.get("fibonacci")
render_ohlcv_snapshot_narrative(
    symbol=symbol,
    timeframe=tf,
    candles=candles,
    indicators=indicators,
    patterns=patterns,
    fibonacci=fib if isinstance(fib, dict) else None,
)

st.subheader("Fibonacci retracements (swing high/low)")
if fib:
    st.json(fib)

st.subheader("Pattern education")
if patterns:
    choice = st.selectbox("Select detected pattern", [p.get("name", "") for p in patterns])
    render_pattern_education(choice)
else:
    st.write("No patterns detected on this window — try a longer history or different timeframe.")

st.subheader("Live WebSocket stream (API `/api/v1/ws/market/{symbol}`)")
col_a, col_b = st.columns([1, 1])
with col_a:
    enable = st.toggle("Connect live stream", value=False)
with col_b:
    refresh = st.button("Drain latest WS message")

if enable:
    ws_key = (symbol, base)
    if st.session_state.get("ws_key") != ws_key:
        if st.session_state.get("ws_client"):
            st.session_state.ws_client.stop()
        st.session_state.ws_client = MarketIntelWebSocketClient(base, symbol)
        st.session_state.ws_client.start()
        st.session_state.ws_key = ws_key
    latest = st.session_state.ws_client.drain()
    if latest:
        st.json(latest.get("tick"))
        mini = latest.get("candles") or []
        if mini:
            st.caption(f"Built {len(mini)} micro-candles server-side (1m bucket).")
else:
    if st.session_state.get("ws_client"):
        st.session_state.ws_client.stop()
        st.session_state.pop("ws_client", None)
        st.session_state.pop("ws_key", None)

if refresh and st.session_state.get("ws_client"):
    st.write(st.session_state.ws_client.drain())

