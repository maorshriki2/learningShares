from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(
    page_title="Market Intel",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_terminal_theme()

api_base = ensure_api_base()
st.title("Market Intel")
st.caption("LearningShares — professional learning terminal, simplified for beginners")
st.markdown(
    f"""
<div class="terminal-panel">
  <p class="terminal-title">API endpoint</p>
  <p>Backend should be running at <span class="metric-glow">{api_base}</span></p>
  <p>Start from <strong>00 — Start Here</strong>, then continue with the guided sidebar checklist.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.text_input("API base URL", value=api_base, key="api_base_input")
    if st.button("Apply API base"):
        st.session_state.api_base = st.session_state.api_base_input.strip().rstrip("/")
        st.success("Updated — reload pages to use new base.")

st.info("Run API + UI together: `python scripts/run_app.py` then open `00 — Start Here` in the sidebar.")
