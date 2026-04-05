from __future__ import annotations

import streamlit as st

from market_intel.modules.charting.education.pattern_psychology import explain_pattern


def render_pattern_education(pattern_name: str) -> None:
    edu = explain_pattern(pattern_name)
    st.markdown(f"### {edu.title}")
    st.write(edu.psychology)
    if edu.historical_note:
        st.caption(edu.historical_note)
    if edu.win_rate_context:
        st.info(edu.win_rate_context)
