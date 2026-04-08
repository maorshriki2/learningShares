from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from market_intel.ui.state.session import normalize_api_public_url

_CACHE_KEY = "_mi_analysis_cache"
_VAULT_KEY = "analysis_data"


def _root() -> dict[str, Any]:
    root = st.session_state.get(_CACHE_KEY)
    if isinstance(root, dict):
        return root
    st.session_state[_CACHE_KEY] = {}
    return st.session_state[_CACHE_KEY]


def cache_namespace(symbol: str, api_base: str) -> str:
    base = normalize_api_public_url(api_base or "")
    return f"{(symbol or '').strip().upper()}|{base}"


def has_namespace(symbol: str, api_base: str) -> bool:
    ns = cache_namespace(symbol, api_base)
    root = _root()
    return isinstance(root.get(ns), dict)


def get_cached(symbol: str, api_base: str, key: str) -> Any | None:
    ns = cache_namespace(symbol, api_base)
    root = _root()
    bucket = root.get(ns)
    if not isinstance(bucket, dict):
        return None
    return bucket.get(key)


def set_cached(symbol: str, api_base: str, key: str, value: Any) -> None:
    ns = cache_namespace(symbol, api_base)
    root = _root()
    bucket = root.get(ns)
    if not isinstance(bucket, dict):
        bucket = {}
        root[ns] = bucket
    bucket[key] = value
    # Also write into a user-facing vault for strict UI separation:
    # st.session_state["analysis_data"][namespace][key] = value
    try:
        vault = st.session_state.get(_VAULT_KEY)
        if not isinstance(vault, dict):
            vault = {}
            st.session_state[_VAULT_KEY] = vault
        vb = vault.get(ns)
        if not isinstance(vb, dict):
            vb = {}
            vault[ns] = vb
        vb[key] = value
    except Exception:
        # Never let vault writes break rendering.
        pass


def clear_symbol(symbol: str, api_base: str) -> None:
    ns = cache_namespace(symbol, api_base)
    root = _root()
    root.pop(ns, None)


def get_or_fetch(
    *,
    symbol: str,
    api_base: str,
    key: str,
    fetcher: Callable[[], Any],
) -> Any:
    cached = get_cached(symbol, api_base, key)
    if cached is not None:
        return cached
    value = fetcher()
    set_cached(symbol, api_base, key, value)
    return value


def require_cached(symbol: str, api_base: str, key: str, *, message_he: str) -> Any:
    """
    Enforce "no API calls inside tabs":
    - If data isn't already cached (via sidebar Analyze), stop the page early.
    """
    v = get_cached(symbol, api_base, key)
    if v is None:
        st.info(message_he)
        st.stop()
    return v

