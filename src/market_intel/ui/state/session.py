from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
import streamlit as st

# נתיב שחייב להופיע ב-openapi.json כדי ש-Blind CSV יעבוד (מונע שרת ישן על 8000).
_OPENAPI_BLIND_ANALYZE = "/api/v1/blindtest/analyze-scenario"

# טיקרים שמורים לתרגול/אנונימי — לא קיימים בבורסה; לא שולחים אותם ל-API.
PLACEHOLDER_SYMBOLS: frozenset[str] = frozenset(
    {
        "ANONY",
        "ANON",
        "ANONYMOUS",
        "UNKNOWN",
        "NONE",
        "N/A",
        "NA",
        "TBD",
        "TODO",
        "PLACEHOLDER",
        "TEST",
        "DUMMY",
    }
)
_SESSION_LAST_REAL = "_mi_last_real_symbol"


def is_placeholder_symbol(symbol: str | None) -> bool:
    s = (symbol or "").strip().upper()
    return not s or s in PLACEHOLDER_SYMBOLS


def resolve_symbol_for_api(symbol: str | None, *, default: str = "AAPL") -> str:
    """
    ממפה טיקר תצוגה (למשל ANONY) לטיקר אמיתי לבקשות API — אחרון תקף או ברירת מחדל.
    """
    s = (symbol or "").strip().upper()
    if not is_placeholder_symbol(s):
        try:
            st.session_state[_SESSION_LAST_REAL] = s
        except Exception:
            pass
        return s
    try:
        last = st.session_state.get(_SESSION_LAST_REAL)
    except Exception:
        last = None
    last_u = (last or "").strip().upper() if isinstance(last, str) else ""
    if last_u and not is_placeholder_symbol(last_u):
        return last_u
    return default


def normalize_api_public_url(url: str) -> str:
    """
    httpx client paths are absolute from host root, e.g. /api/v1/...
    If the user (or env) sets API_PUBLIC_URL to .../api/v1, requests would
    become .../api/v1/api/v1/... and return 404.
    """
    u = (url or "").strip().rstrip("/")
    lower = u.lower()
    if lower.endswith("/api/v1"):
        u = u[: -len("/api/v1")].rstrip("/")
    return u or "http://127.0.0.1:8000"


def get_api_base() -> str:
    return normalize_api_public_url(os.environ.get("API_PUBLIC_URL", "http://127.0.0.1:8000"))


def ensure_api_base() -> str:
    if "api_base" not in st.session_state:
        st.session_state.api_base = get_api_base()
    return normalize_api_public_url(str(st.session_state.api_base))


def discover_api_base_with_blind_analyze_route(
    *,
    preferred_base: str | None = None,
    host: str = "127.0.0.1",
    port_start: int = 8000,
    port_end: int = 8020,
) -> str | None:
    """
    סורק פורטים מקומיים ומחזיר base URL של API שב-openapi שלו רשום analyze-scenario.
    מתאים כשעל 8000 רץ תהליך ישן והמעודכן על 8001+.
    """
    to_try: list[str] = []
    if preferred_base:
        to_try.append(normalize_api_public_url(preferred_base))
    try:
        pu = urlparse(preferred_base or "")
        if pu.hostname:
            host = pu.hostname
    except Exception:
        pass
    for p in range(port_start, port_end + 1):
        b = f"http://{host}:{p}"
        if b not in to_try:
            to_try.append(b)
    for base in to_try:
        try:
            r = httpx.get(f"{base}/openapi.json", timeout=1.8)
            if r.status_code != 200:
                continue
            paths = r.json().get("paths") or {}
            if _OPENAPI_BLIND_ANALYZE in paths:
                return base
        except Exception:
            continue
    return None
