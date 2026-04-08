from __future__ import annotations

from datetime import datetime
import math

import streamlit as st
import httpx

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.watchlist_universe import WATCHLIST_GROUPS
from market_intel.ui.formatters.bidi_text import num_embed as N
from market_intel.ui.formatters.usd_compact import format_usd_compact
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="Watchlist", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("watchlist")

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("👁️ Watchlist — סקטורים + Large/Mid/Small")
st.caption(
    "מטרה: רשימת מעקב מהירה שמתרעננת בלי להריץ מודלים כבדים. "
    "הטבלה כאן היא Snapshot + רענון מחיר מהיר (near‑real‑time), לא ניתוח מלא."
)
last_ts = st.session_state.get("_watchlist_last_updated_ts")
if isinstance(last_ts, str) and last_ts.strip():
    st.caption(f"**Last Watchlist update:** {last_ts}")
section_divider()
st.info(
    "מה עושים פה ב‑30 שניות: בוחרים סקטורים → מקבלים Top‑N בכל Bucket (Large/Mid/Small) "
    "→ אם משהו מעניין, עוברים ל‑Start/Stock 360 לניתוח מלא."
)
col_clear, col_refresh, col_spacer = st.columns([1.3, 1.4, 3.3])
with col_clear:
    if st.button(
        "Clear cache",
        help="מנקה cache מקומי (Snapshot + fallback) — שימושי אם קודם היו תקלות ספק והכל יצא n/a.",
    ):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun()


def _cap_bucket(market_cap: float | None) -> str | None:
    if market_cap is None or not math.isfinite(float(market_cap)):
        return None
    mc = float(market_cap)
    if mc >= 10_000_000_000:
        return "Large Cap"
    if mc >= 2_000_000_000:
        return "Mid Cap"
    if mc >= 300_000_000:
        return "Small Cap"
    return None


@st.cache_data(ttl=30, show_spinner=False)
def _sector_buckets_cached(api_base: str, sectors: list[str], large_n: int, mid_n: int, small_n: int) -> dict:
    c = MarketIntelApiClient(api_base)
    try:
        return c.watchlist_sector_buckets(
            sectors=sectors,
            large_n=int(large_n),
            mid_n=int(mid_n),
            small_n=int(small_n),
        )
    finally:
        c.close()

@st.cache_data(ttl=5 * 60, show_spinner=False)
def _summary_cached(symbol: str, api_base: str) -> dict:
    """
    Fallback path when dynamic watchlist screener is unavailable.
    """
    c = MarketIntelApiClient(api_base)
    try:
        return c.instrument_summary(symbol)
    except httpx.HTTPStatusError as exc:
        sym = (symbol or "").strip().upper()
        if exc.response is not None and exc.response.status_code == 404:
            st.warning(
                "ה‑API לא מכיר את endpoint `instruments/{symbol}/summary` (ישן/לא עודכן). "
                "הרץ מחדש את השרת."
            )
        elif exc.response is not None and 500 <= exc.response.status_code <= 599:
            st.warning(
                f"השרת החזיר שגיאת 5xx עבור `{sym}`. ממשיכים בלי להפיל את המסך — נסה רענון מאוחר יותר."
            )
        return {
            "symbol": sym,
            "name": None,
            "sector": None,
            "market_cap": None,
            "price": None,
            "beta": None,
            "volatility_1y": None,
        }
    finally:
        c.close()


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{float(x) * 100:.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_float(x: float | None, nd: int = 2) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "n/a"


selected_keys = st.multiselect(
    "בחר תתי-קטגוריות להצגה (מוצגות יחד בכל bucket)",
    options=[g.key for g in WATCHLIST_GROUPS],
    default=[g.key for g in WATCHLIST_GROUPS],
    format_func=lambda k: next((g.title_he for g in WATCHLIST_GROUPS if g.key == k), k),
)
selected_groups = [g for g in WATCHLIST_GROUPS if g.key in set(selected_keys)]
if not selected_groups:
    st.warning("בחר לפחות תת-קטגוריה אחת.")
    st.stop()

sector_names = {
    "technology": "Technology",
    "healthcare": "Healthcare",
    "consumer": "Consumer Cyclical",
    "banking": "Financial Services",
    "defense": "Industrials",
    "space": "Industrials",
    "drones": "Industrials",
}
selected_sectors = [sector_names.get(g.key) for g in selected_groups if sector_names.get(g.key)]
selected_sectors = list(dict.fromkeys(selected_sectors))

col_a, col_b, col_c = st.columns([1.2, 1.2, 2.6])
large_n = col_a.number_input("Top‑N Large", min_value=1, max_value=15, value=5, step=1)
mid_n = col_b.number_input("Top‑N Mid", min_value=1, max_value=15, value=5, step=1)
small_n = col_c.number_input("Top‑N Small", min_value=1, max_value=15, value=5, step=1)

refresh = st.button("רענן עכשיו (מחיר/דירוג)", type="primary")
if refresh:
    _sector_buckets_cached.clear()  # force reload of near-real-time snapshot

with st.spinner("טוען Watchlist (Snapshot מהיר + מחיר עדכני)..."):
    rows: list[dict] = []
    screener_payload = _sector_buckets_cached(base, selected_sectors, int(large_n), int(mid_n), int(small_n))
    st.session_state["_watchlist_last_updated_ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ok = bool(screener_payload.get("ok", True))
    buckets = screener_payload.get("buckets") if isinstance(screener_payload, dict) else None
    total_bucket_items = 0
    if isinstance(buckets, dict):
        for _sec, per_bucket in buckets.items():
            if isinstance(per_bucket, dict):
                for _bn, items in per_bucket.items():
                    if isinstance(items, list):
                        total_bucket_items += len(items)

    # Sometimes providers return ok=true but empty lists (rate-limits/plan restrictions).
    # In that case we still want to fall back to the known-tickers universe.
    if ok and isinstance(buckets, dict) and buckets and total_bucket_items > 0:
        # Flatten: sector -> bucket -> items
        for sec, per_bucket in buckets.items():
            if not isinstance(per_bucket, dict):
                continue
            for bucket_name, items in per_bucket.items():
                if not isinstance(items, list):
                    continue
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    r = {
                        "symbol": it.get("symbol"),
                        "name": it.get("name"),
                        "sector": it.get("sector") or sec,
                        "market_cap": it.get("market_cap"),
                        "price": it.get("price"),
                        "beta": it.get("beta"),
                        "volatility_1y": None,  # intentionally omitted from fast screener
                        "_bucket": str(bucket_name),
                        "_group_key": str(sec),
                        "_group_title_he": str(sec),
                        "_source": it.get("source") or "watchlist.sector-buckets",
                    }
                    rows.append(r)
        st.caption(f"Snapshot מתרענן אוטומטית כל **{N('~30')}** שניות (cache TTL) או בלחיצה על רענון.")
    else:
        msg = screener_payload.get("message") if isinstance(screener_payload, dict) else None
        st.warning(
            "ה‑Watchlist הדינמי לא זמין כרגע. עוברים למצב fallback (איטי יותר) על יקום טיקרים ידוע."
        )
        if msg:
            st.caption(str(msg))
        for g in selected_groups:
            for t in g.tickers:
                s = _summary_cached(t, base)
                s["_bucket"] = _cap_bucket(s.get("market_cap"))
                s["_group_key"] = g.key
                s["_group_title_he"] = g.title_he
                s["_source"] = "fallback.instrument_summary"
                rows.append(s)

with st.expander("Debug — נתוני Watchlist (לפתרון תקלות)", expanded=False):
    st.write({"api_base": base, "selected_groups": [g.key for g in selected_groups]})
    st.write({"selected_sectors": selected_sectors})
    st.write({"rows_source_counts": {}})
    missing_caps = [r.get("symbol") for r in rows if r.get("market_cap") is None]
    st.write(
        {
            "tickers_total": len(rows),
            "missing_market_cap": len(missing_caps),
        }
    )
    if missing_caps:
        st.caption("טיקרים שחזרו בלי Market Cap:")
        st.write(missing_caps)


def _bucket_rows_by_group(bucket: str, group_key: str) -> list[dict]:
    rs = [
        r
        for r in rows
        if r.get("_bucket") == bucket
        and r.get("_group_key") == group_key
        and r.get("market_cap") is not None
    ]
    rs.sort(key=lambda r: float(r.get("market_cap") or 0), reverse=True)
    # already top-N on screener path; keep cap to avoid UI explosion on fallback
    return rs[: max(int(large_n), int(mid_n), int(small_n), 5)]


def _bucket_all_rows(bucket: str) -> list[dict]:
    rs = [r for r in rows if r.get("_bucket") == bucket and r.get("market_cap") is not None]
    return rs


large_all = _bucket_all_rows("Large Cap")
mid_all = _bucket_all_rows("Mid Cap")
small_all = _bucket_all_rows("Small Cap")

st.subheader("📌 Watchlist — חזקות לפי שווי שוק (Top 5 לכל תת-קטגוריה, מוצג יחד)")
st.caption(
    f"נמצאו בסך הכל: Large={len(large_all)}, Mid={len(mid_all)}, Small={len(small_all)}. "
    f"מציגים עד 5 לכל תת-קטגוריה בכל טאב (לכן למשל 3 תתי-קטגוריות ⇒ עד 15 שורות)."
)
tab_l, tab_m, tab_s = st.tabs(["Large Cap", "Mid Cap", "Small Cap"])


def _render_bucket(bucket_name: str, items: list[dict]) -> None:
    if not items:
        st.info("לא נמצאו מספיק מניות בקבוצה הזו (לפי היקום המוגדר/נתונים חסרים).")
        return

    header = st.columns([1.2, 2.2, 1.6, 1.4, 1.6, 1.0])
    header[0].markdown("**Ticker**")
    header[1].markdown("**Name**")
    header[2].markdown("**Market Cap**")
    header[3].markdown("**Price**")
    header[4].markdown("**Volatility (1Y)**")
    header[5].markdown("**Beta**")

    for r in items:
        sym = r.get("symbol") or ""
        cols = st.columns([1.2, 2.2, 1.6, 1.4, 1.6, 1.0])
        cols[0].code(sym, language=None)
        cols[1].write(r.get("name") or "—")
        mc = r.get("market_cap")
        cols[2].write(format_usd_compact(float(mc)) if mc is not None else "n/a")
        px = r.get("price")
        cols[3].write(f"{float(px):.2f} $" if px is not None else "n/a")
        cols[4].write(_fmt_pct(r.get("volatility_1y")))
        cols[5].write(_fmt_float(r.get("beta")))


def _render_bucket_all_groups(bucket_name: str) -> None:
    # Dynamic mode groups by sector string; fallback uses WATCHLIST_GROUPS keys.
    group_keys = sorted({str(r.get("_group_key") or "") for r in rows if str(r.get("_group_key") or "")})
    for gk in group_keys:
        title = gk
        items = _bucket_rows_by_group(bucket_name, gk)
        st.markdown(f"### {title}")
        _render_bucket(bucket_name, items)
        st.divider()


with tab_l:
    _render_bucket_all_groups("Large Cap")
with tab_m:
    _render_bucket_all_groups("Mid Cap")
with tab_s:
    _render_bucket_all_groups("Small Cap")

section_divider()
st.caption("Watchlist בלבד — ניתוח מלא נמצא ב־Stock 360 (Final Verdict) ובדפים הייעודיים.")
