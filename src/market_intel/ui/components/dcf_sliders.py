from __future__ import annotations

import streamlit as st


def dcf_controls() -> tuple[float, float, float]:
    st.markdown("#### DCF assumptions")
    growth = st.slider("High-stage revenue/FCF growth", 0.0, 0.25, 0.05, 0.005, help="Illustrative constant growth in explicit stage.")
    terminal = st.slider("Terminal growth", 0.0, 0.06, 0.02, 0.001)
    wacc = st.slider("WACC", 0.04, 0.20, 0.09, 0.001)
    return growth, terminal, wacc
