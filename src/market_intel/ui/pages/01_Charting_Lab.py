from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.clients.ws_client import MarketIntelWebSocketClient
from market_intel.ui.components.active_recall import render_active_recall_checkpoint
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.chart_plotly import build_candlestick_figure
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.chart_snapshot_narrative import render_ohlcv_snapshot_narrative
from market_intel.ui.components.education_sidebar import render_pattern_education
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.guided_learning import render_guided_learning_sidebar
from market_intel.ui.components.mentor_expander import MENTOR_CHARTING, render_mentor
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="Charting Lab", layout="wide")
inject_terminal_theme()
inject_card_css()

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("📈 Charting Lab — מעבדת גרפים")
render_mentor(MENTOR_CHARTING)
render_glossary_terms(["MACD", "VWAP"])
section_divider()
symbol = st.text_input("Symbol", value=st.session_state.get("guided_symbol", "AAPL")).strip().upper()
symbol = render_guided_learning_sidebar("charting", symbol, show_symbol_input=False)
tf = st.selectbox(
    "Timeframe",
    ["1mo", "1wk", "1d", "1h", "15m", "5m", "1m"],
    index=2,
    help="עד לאחרונה הוגדר רק עד יומי כדי לפשט את המעבדה ואת המיפוי ל-yfinance; נוספו שבועי וחודשי לתמונה ארוכת טווח.",
)
if not symbol.strip():
    st.warning("Please enter a valid ticker symbol.")
    st.stop()

try:
    payload = client.ohlcv(symbol, timeframe=tf, limit=320)
except Exception as exc:
    st.error(f"API error: {exc}")
    st.stop()

candles = payload.get("candles") or []
indicators = payload.get("indicators") or {}
patterns = payload.get("patterns") or []

fig = build_candlestick_figure(candles, indicators, patterns)
st.plotly_chart(fig, width="stretch")
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

section_divider()
render_active_recall_checkpoint(
    page_key="charting",
    prompt="אם ה-RSI נמצא מעל 70, מה זה לרוב מסמן?",
    choices=[
        "מכירת יתר וסיכוי גבוה לקפיצה מיידית",
        "קניית יתר ועלייה אפשרית בסיכון לתיקון",
        "שהמניה זולה פונדמנטלית",
        "שאין משמעות לאינדיקטור",
    ],
    correct_index=1,
    explanation="RSI מעל 70 נתפס כאזור קניית יתר. זה לא מבטיח ירידה מיידית, אבל מעלה את הסיכון לתנודתיות/תיקון.",
)
