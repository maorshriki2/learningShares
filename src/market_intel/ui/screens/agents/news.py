from __future__ import annotations

import streamlit as st

from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import section_divider
from market_intel.ui.components.market_context_feed_panel import render_market_context_feed
from market_intel.ui.state.analysis_cache import get_cached, require_cached, set_cached
from market_intel.ui.state.session import ensure_api_base


def render() -> None:
    base = ensure_api_base()
    client = MarketIntelApiClient(base)

    st.title("📡 הקשר שוק — חדשות, נאומים, שמועות, אירועי חברה")
    st.caption(
        "שכבה עתידית למקורות חיצוניים שמסבירים למה המניה “מתנהגת עכשיו”. "
        "הדף מציג נתונים מה־Artifact (Analysis) ובאופציה גם טעינה חיה מה־API."
    )
    section_divider()

    symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"

    col_a, col_b = st.columns([1.0, 2.0])
    refresh_live = col_a.button(
        "רענון חי מה־API",
        help="מבצע קריאה ל־/context-feed ושומר ב־cache עבור הדף הזה.",
    )
    if refresh_live:
        try:
            live = client.market_context_feed(symbol)
            if isinstance(live, dict) and live.get("ok", True):
                set_cached(symbol, base, "market_context_feed:v1", live)
                col_b.success("עודכן בהצלחה.")
            else:
                col_b.warning("ה־API החזיר payload לא תקין.")
        except Exception as exc:
            col_b.error(f"Live refresh failed: {type(exc).__name__}: {exc}")

    direct = get_cached(symbol, base, "market_context_feed:v1")
    if isinstance(direct, dict) and direct:
        payload = direct
    else:
        artifact = require_cached(
            symbol,
            base,
            "analysis_artifact:v1",
            message_he="אין Artifact שמור. לחץ **ניתוח** בסיידבר כדי לטעון את כל הטאבים פעם אחת.",
        )
        inputs = artifact.get("inputs") if isinstance(artifact, dict) else {}
        payload = inputs.get("market_context_feed") if isinstance(inputs, dict) else {}

    render_market_context_feed(payload)
    st.caption("Educational only — verify all items against primary sources.")

