from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.governance_panel import render_governance
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.mentor_expander import MENTOR_GOVERNANCE, render_mentor
from market_intel.ui.components.sentiment_highlights import render_sentiment
from market_intel.ui.state.session import ensure_api_base
from market_intel.ui.state.analysis_cache import require_cached

st.set_page_config(page_title="Governance & NLP", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("governance")

base = ensure_api_base()

st.title("🏛️ Governance, SEC Filings & FinBERT Sentiment")
render_mentor(MENTOR_GOVERNANCE)
render_glossary_terms(["Altman Z"])
section_divider()
symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"
artifact = require_cached(
    symbol,
    base,
    "analysis_artifact:v1",
    message_he="אין Artifact שמור. לחץ **ניתוח** בסיידבר כדי לטעון, או החזר ל־2024/Q4.",
)
meta = artifact.get("meta") if isinstance(artifact, dict) else {}
cfg = meta.get("config") if isinstance(meta, dict) else {}
year = int(cfg.get("gov_year") or 2024)
quarter = int(cfg.get("gov_quarter") or 4)
inputs = artifact.get("inputs") if isinstance(artifact, dict) else {}
gov = inputs.get("governance") if isinstance(inputs, dict) else {}

tab_dash, tab_narrative = st.tabs(["לוח בקרה", "Analyst Narrative"])

with tab_dash:
    render_governance(gov)
    render_sentiment(gov)

with tab_narrative:
    st.markdown("### ניתוח נרטיבי — שיחת רווחים (Claude)")
    st.caption(
        "סיכום אוטומטי של טקסט ה־earnings call (מקור: Finnhub כשמוגדר מפתח, אחרת דמו). "
        "דורש `ANTHROPIC_API_KEY` ב־.env."
    )
    nar = inputs.get("analyst_narrative") if isinstance(inputs, dict) else {}
    if isinstance(nar, dict) and nar.get("ok"):
        src = nar.get("source", "")
        if src:
            st.caption(f"מקור טקסט: **{src}**")
        strengths = nar.get("strengths_he") or []
        risks = nar.get("risks_hedged_he") or []
        sent = nar.get("sentiment_vs_prior_he") or ""
        st.markdown("#### שלוש נקודות חוזק (לפי הנהלה)")
        for i, s in enumerate(strengths[:3], 1):
            st.markdown(f"{i}. {s}")
        st.markdown("#### שלושה סיכונים / ניסוחים מגוננים")
        for i, s in enumerate(risks[:3], 1):
            st.markdown(f"{i}. {s}")
        st.markdown("#### סנטימנט מול הרבעון הקודם")
        st.markdown(sent or "—")
    else:
        msg = nar.get("message_he") if isinstance(nar, dict) else None
        st.info(msg or "לא זמין.")
