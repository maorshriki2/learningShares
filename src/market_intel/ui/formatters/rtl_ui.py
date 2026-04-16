from __future__ import annotations

"""Small RTL helpers for Streamlit UI.

The app defaults to RTL via ``ui/assets/theme.css``. This module is for cases where we want
an explicit RTL/LTR island in the middle of markdown (mixed Hebrew + tickers/paths).
"""

import html

from market_intel.ui.formatters.bidi_text import md_code

# A lightweight, explicit RTL mark. Sometimes useful for copy/paste / edge punctuation.
RLM = "\u200f"


def rtl_div(text: str, *, tag: str = "div") -> str:
    """Return an explicit RTL HTML block with right alignment."""
    safe = html.escape(text or "", quote=False).replace("\n", "<br>")
    return (
        f'<{tag} dir="rtl" style="text-align:right; unicode-bidi:plaintext;">'
        f"{safe}"
        f"</{tag}>"
    )


def st_rtl(text: str) -> None:
    """Render a plain RTL block in Streamlit."""
    import streamlit as st

    st.markdown(rtl_div(text), unsafe_allow_html=True)


def he_mixed(*parts: str) -> str:
    """Build a Hebrew sentence with embedded LTR code fragments.

    Example:
        st.markdown(he_mixed("הטיקר ", md_code("AAPL"), " עודכן בהצלחה"), unsafe_allow_html=True)
    """
    return "".join(parts)

