from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.stock360_composed_panel import render_stock360_composed_panel
from market_intel.ui.state.session import ensure_api_base
from market_intel.ui.state.analysis_cache import require_cached

st.set_page_config(page_title="Stock 360° View", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("stock360")

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("Stock 360° View — Composed (Artifact v1)")
st.caption(
    "המסך מציג פסק דין 360 שמורכב מ־Valuation + Chart + Market Context (כשזמין). "
    "הנתונים נטענים פעם אחת ב־Analyze ונקראים מתוך Artifact."
)
section_divider()

symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"

col_a, col_b, col_c = st.columns([1.6, 1.4, 1.0])
with col_a:
    horizons = st.multiselect(
        "Forecast horizons (days)",
        options=[30, 90, 180, 365],
        default=[30, 90, 365],
        help="ימים קלנדריים (30/90/365). בצד השרת מומרים בקירוב לימי מסחר לצורך החישוב.",
    )
with col_b:
    include_explain = st.toggle("Include explain payload", value=True)

section_divider()

artifact = require_cached(
    symbol,
    base,
    "analysis_artifact:v1",
    message_he="אין Artifact שמור. לחץ **ניתוח** בסיידבר כדי לטעון את כל הטאבים פעם אחת.",
)
result = artifact.get("stock360") if isinstance(artifact, dict) else None
if not isinstance(result, dict):
    st.info("אין Stock360 זמין בתוך ה־Artifact.")
    st.stop()

render_stock360_composed_panel(result, include_explain=include_explain)
