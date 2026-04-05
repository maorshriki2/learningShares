from __future__ import annotations

import os

import streamlit as st


def get_api_base() -> str:
    return os.environ.get("API_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")


def ensure_api_base() -> str:
    if "api_base" not in st.session_state:
        st.session_state.api_base = get_api_base()
    return st.session_state.api_base
