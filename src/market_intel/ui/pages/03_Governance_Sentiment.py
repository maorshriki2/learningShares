from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.active_recall import render_active_recall_checkpoint
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.governance_panel import render_governance
from market_intel.ui.components.guided_learning import render_guided_learning_sidebar
from market_intel.ui.components.mentor_expander import MENTOR_GOVERNANCE, render_mentor
from market_intel.ui.components.sentiment_highlights import render_sentiment
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="Governance & NLP", layout="wide")
inject_terminal_theme()
inject_card_css()

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("🏛️ Governance, SEC Filings & FinBERT Sentiment")
render_mentor(MENTOR_GOVERNANCE)
render_glossary_terms(["Altman Z"])
section_divider()
symbol = st.text_input(
    "Symbol",
    value=st.session_state.get("guided_symbol", "AAPL"),
).strip().upper()
symbol = render_guided_learning_sidebar("governance", symbol, show_symbol_input=False)
year = st.number_input("Earnings year", min_value=2018, max_value=2026, value=2024)
quarter = st.number_input("Quarter", min_value=1, max_value=4, value=4)

try:
    gov = client.governance_dashboard(symbol, int(year), int(quarter))
except Exception as exc:
    st.error(f"API error: {exc}")
    st.stop()

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
    try:
        nar = client.analyst_narrative(symbol, int(year), int(quarter))
    except Exception as exc:
        st.error(f"שגיאת API: {exc}")
    else:
        if nar.get("ok"):
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
            msg = nar.get("message_he") or "לא זמין."
            st.info(msg)

section_divider()
render_active_recall_checkpoint(
    page_key="governance",
    prompt="איזה שילוב נחשב לרוב נורת אזהרה התנהגותית?",
    choices=[
        "רכישות אינסיידר גבוהות ושקיפות גבוהה",
        "מכירות אינסיידר מסיביות שאינן מתוכננות מראש",
        "דוח 8-K חיובי",
        "עלייה בציון חיובי של FinBERT",
    ],
    correct_index=1,
    explanation=(
        "מכירות אינסיידר חריגות ולא מתוכננות מראש עשויות להעיד על חשש פנימי "
        "לגבי התמחור או הסיכון."
    ),
)
