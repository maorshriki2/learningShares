from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

_STATE_KEY = "favorite_symbols"
_MAX_FAVORITES = 10


def _favorites_path() -> Path:
    # Keep it per-user (works on Windows/macOS/Linux).
    return Path.home() / ".learningshares" / "favorites.json"


def _normalize_symbol(sym: str) -> str:
    return (sym or "").strip().upper()


def _load_from_disk() -> list[str]:
    p = _favorites_path()
    try:
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return []
        syms = data.get("symbols")
        if not isinstance(syms, list):
            return []
        out: list[str] = []
        for s in syms:
            if not isinstance(s, str):
                continue
            u = _normalize_symbol(s)
            if u and u not in out:
                out.append(u)
        return out[:_MAX_FAVORITES]
    except Exception:
        return []


def _save_to_disk(symbols: list[str]) -> None:
    p = _favorites_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"symbols": symbols[:_MAX_FAVORITES]}
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # If disk is read-only or path fails, keep session state only.
        pass


def get_favorites() -> list[str]:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = _load_from_disk()
    syms = st.session_state.get(_STATE_KEY)
    if not isinstance(syms, list):
        st.session_state[_STATE_KEY] = []
        return []
    # sanitize
    out: list[str] = []
    for s in syms:
        if not isinstance(s, str):
            continue
        u = _normalize_symbol(s)
        if u and u not in out:
            out.append(u)
    out = out[:_MAX_FAVORITES]
    st.session_state[_STATE_KEY] = out
    return out


def set_favorites(symbols: list[str]) -> list[str]:
    out: list[str] = []
    for s in symbols:
        if not isinstance(s, str):
            continue
        u = _normalize_symbol(s)
        if u and u not in out:
            out.append(u)
    out = out[:_MAX_FAVORITES]
    st.session_state[_STATE_KEY] = out
    _save_to_disk(out)
    return out


def add_favorite(symbol: str) -> list[str]:
    u = _normalize_symbol(symbol)
    if not u:
        return get_favorites()
    cur = get_favorites()
    if u in cur:
        return cur
    nxt = (cur + [u])[:_MAX_FAVORITES]
    return set_favorites(nxt)


def remove_favorite(symbol: str) -> list[str]:
    u = _normalize_symbol(symbol)
    cur = get_favorites()
    nxt = [s for s in cur if s != u]
    return set_favorites(nxt)


def move_favorite(symbol: str, direction: int) -> list[str]:
    """
    direction: -1 (up), +1 (down)
    """
    u = _normalize_symbol(symbol)
    cur = get_favorites()
    try:
        i = cur.index(u)
    except ValueError:
        return cur
    j = i + int(direction)
    if j < 0 or j >= len(cur):
        return cur
    cur[i], cur[j] = cur[j], cur[i]
    return set_favorites(cur)

