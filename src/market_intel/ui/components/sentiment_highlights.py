from __future__ import annotations

from typing import Any

import streamlit as st


def render_sentiment(payload: dict[str, Any]) -> None:
    st.subheader("FinBERT highlights")
    bull = payload.get("highlights_bullish") or []
    bear = payload.get("highlights_bearish") or []
    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Bullish-leaning sentences**")
        for s in bull:
            st.success(f"{s.get('label')}: {s.get('text')}")
    with b2:
        st.markdown("**Bearish-leaning sentences**")
        for s in bear:
            st.error(f"{s.get('label')}: {s.get('text')}")
    st.markdown("#### How to read corporate speak")
    st.write(payload.get("corporate_speak_lesson", ""))
