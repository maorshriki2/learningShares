from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.state.favorites import (
    add_favorite,
    get_favorites,
    move_favorite,
    remove_favorite,
    set_favorites,
)
from market_intel.ui.state.session import ensure_api_base, normalize_api_public_url

st.set_page_config(
    page_title="Market Intel",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_terminal_theme()
render_sidebar_nav("favorites")

api_base = ensure_api_base()

st.title("Favorite Stocks")
st.caption("Pick up to 10 tickers and jump quickly to analysis pages.")

favs = get_favorites()

col_add, col_hint = st.columns([1.25, 2.75])
with col_add:
    sym_in = st.text_input("הוסף טיקר", value="", placeholder="למשל: AAPL").strip().upper()
with col_hint:
    st.markdown(
        "טיפ: לחץ על **Select** ליד מניה כדי להדביק אותה בשדה **Symbol** בסיידבר (בלי לבצע ניתוח)."
    )

btn_col1, btn_col2, btn_col3 = st.columns([1.0, 1.0, 3.0])
with btn_col1:
    add_clicked = st.button("הוסף", type="primary", disabled=not bool(sym_in))
with btn_col2:
    clear_clicked = st.button("נקה רשימה", disabled=not bool(favs))
with btn_col3:
    st.caption(f"נשמרו {len(favs)}/10")

if add_clicked and sym_in:
    add_favorite(sym_in)
    st.rerun()

if clear_clicked:
    set_favorites([])
    st.rerun()

st.divider()

favs = get_favorites()
if not favs:
    st.info("עדיין אין מניות מועדפות. הוסף טיקר למעלה (עד 10).")
else:
    for i, sym in enumerate(favs):
        row = st.columns([1.2, 1.0, 1.0, 1.0, 3.0])
        row[0].markdown(f"**{i+1}. {sym}**")
        up_disabled = i == 0
        down_disabled = i == len(favs) - 1

        if row[1].button("↑", key=f"fav_up_{sym}", disabled=up_disabled):
            move_favorite(sym, -1)
            st.rerun()
        if row[2].button("↓", key=f"fav_down_{sym}", disabled=down_disabled):
            move_favorite(sym, +1)
            st.rerun()
        if row[3].button("Select", key=f"fav_select_{sym}"):
            # Only populate the sidebar Symbol input; do not start analysis and do not change pages.
            # The user must click "ניתוח" in the sidebar to refresh cached analysis data.
            # Cannot set a widget's key after it's instantiated in the same run.
            # Defer the update so the sidebar can apply it before rendering the input widget.
            st.session_state["_mi_global_symbol_next"] = sym
            st.rerun()
        if row[4].button("הסר", key=f"fav_remove_{sym}"):
            remove_favorite(sym)
            st.rerun()

with st.sidebar:
    with st.expander("Advanced — API", expanded=False):
        st.text_input("API base URL", value=api_base, key="api_base_input")
        if st.button("Apply API base"):
            st.session_state.api_base = normalize_api_public_url(st.session_state.api_base_input)
            st.success("Updated — reload pages to use new base.")

