from __future__ import annotations

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.components.cards import inject_card_css
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.screens.agents.news import render as render_screen

st.set_page_config(page_title="NEWS AGENT", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("news_agent")

render_screen()

