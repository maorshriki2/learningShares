from __future__ import annotations

import streamlit as st

from market_intel.ui.state.session import ensure_api_base, is_placeholder_symbol, resolve_symbol_for_api
from market_intel.ui.state.prefetch import (
    collect_prefetch_if_ready,
    get_prefetch_status,
    start_prefetch,
)
from market_intel.ui.state.analysis_cache import get_cached
from market_intel.ui.state.analysis_cache import clear_symbol


def render_sidebar_nav(current: str | None = None) -> None:
    """
    Custom sidebar navigation:
    - Keeps the exact order requested
    - Adds a collapsible "core" group (expander)
    - Highlights bottom 3 pages in green
    """
    with st.sidebar:
        st.markdown("### Symbol")
        default_sym = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"
        # Apply any deferred symbol selection *before* instantiating the widget with key `_mi_global_symbol`.
        next_sym = st.session_state.pop("_mi_global_symbol_next", None)
        if isinstance(next_sym, str) and next_sym.strip():
            st.session_state["guided_symbol"] = next_sym.strip().upper()
            st.session_state["_mi_global_symbol"] = next_sym.strip().upper()
        sym_in = st.text_input(
            "Symbol",
            value=default_sym,
            key="_mi_global_symbol",
            help="הסימבול כאן משפיע על כל העמודים.",
        )
        sym_norm = (sym_in or "").strip().upper() or default_sym
        api_base = ensure_api_base()

        # Artifact config (used by Analyze to build a single unified artifact).
        # Tabs do not recompute; they only render the last analyzed artifact.
        with st.expander("Analysis settings", expanded=False):
            tf = st.selectbox("Timeframe", ["1d", "1wk", "1mo"], index=0, key="_mi_cfg_timeframe")
            limit = st.slider("Bars (limit)", min_value=120, max_value=1100, value=320, step=10, key="_mi_cfg_limit")
            years = st.slider("Fundamentals years", min_value=3, max_value=20, value=10, step=1, key="_mi_cfg_years")
            gov_year = st.number_input("Governance year", min_value=2018, max_value=2026, value=2024, step=1, key="_mi_cfg_gov_year")
            gov_quarter = st.number_input("Governance quarter", min_value=1, max_value=4, value=4, step=1, key="_mi_cfg_gov_quarter")
            peers_extra = st.text_input("Peers extra (comma-separated)", value="", key="_mi_cfg_peers_extra")
            st.markdown("**Valuation verdict settings**")
            mos_required = st.slider("MOS required", min_value=0.0, max_value=0.6, value=0.15, step=0.01, key="_mi_cfg_mos_required")
            premium_threshold = st.slider("Premium threshold", min_value=0.0, max_value=1.0, value=0.15, step=0.01, key="_mi_cfg_premium_threshold")
            wacc_span = st.slider("WACC span (±)", min_value=0.0, max_value=0.2, value=0.02, step=0.005, key="_mi_cfg_wacc_span")
            terminal_span = st.slider("Terminal g span (±)", min_value=0.0, max_value=0.1, value=0.01, step=0.0025, key="_mi_cfg_terminal_span")
            grid_size = st.selectbox("Sensitivity grid size", options=[3, 5, 7, 9], index=1, key="_mi_cfg_grid_size")

            st.session_state["_mi_analysis_config"] = {
                "timeframe": tf,
                "limit": int(limit),
                "years": int(years),
                "gov_year": int(gov_year),
                "gov_quarter": int(gov_quarter),
                "peers_extra": str(peers_extra or ""),
                "mos_required": float(mos_required),
                "premium_threshold": float(premium_threshold),
                "wacc_span": float(wacc_span),
                "terminal_span": float(terminal_span),
                "grid_size": int(grid_size),
            }

        # Background prefetch: do not advance work on rerun.
        # If the background job finished, cache the results now (fast, local memory writes only).
        collect_prefetch_if_ready()

        c_sp1, c_mid, c_sp2 = st.columns([1.0, 1.6, 1.0])
        run = c_mid.button("ניתוח", type="primary", use_container_width=True)

        if run:
            st.session_state["guided_symbol"] = sym_norm
            # Reset the dots immediately on re-analysis.
            clear_symbol(resolve_symbol_for_api(sym_norm), api_base)
            start_prefetch(
                symbol_display=sym_norm,
                api_base=api_base,
                start_tab=current,
                config=st.session_state.get("_mi_analysis_config") if isinstance(st.session_state.get("_mi_analysis_config"), dict) else None,
            )
            st.rerun()

        pf = get_prefetch_status()
        if isinstance(pf, dict) and pf.get("active"):
            # While a background job runs, we need occasional reruns to reflect live progress
            # and to collect completed step results into the local cache. This is lightweight
            # now (no network calls on rerun), so it shouldn't block the UI.
            try:
                from streamlit_autorefresh import st_autorefresh

                # Keep the UI readable: refresh progress occasionally (not constantly).
                st_autorefresh(interval=1500, key=f"_mi_prefetch_live_{pf.get('job_id') or 'job'}")
            except Exception:
                pass

            sym_pf = str(pf.get("symbol") or "").strip().upper()
            cur = pf.get("current_label") or "…"
            done_n = int(pf.get("done_n") or 0)
            total_n = int(pf.get("total_n") or 0)
            st.markdown(f"**Prefetch: {sym_pf or '—'}**")
            if total_n > 0:
                st.progress(min(max(done_n / float(total_n), 0.0), 1.0))
            st.caption(f"{cur} ({done_n}/{total_n})")
            err = pf.get("error")
            if err:
                st.error(f"Prefetch failed: {err}")

        last = st.session_state.get("_mi_last_analysis_sync")
        if isinstance(last, dict):
            ts = str(last.get("ts") or "").strip()
            sym_last = str(last.get("symbol") or "").strip().upper()
            if sym_last:
                st.markdown(f"**{sym_last}**")
            if ts:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(ts)
                    d = dt.date().isoformat()
                    t = dt.time().isoformat(timespec="seconds")
                except Exception:
                    d, t = "", ""
                # Tighter vertical spacing than st.caption (which adds margin).
                lines: list[str] = []
                if d:
                    lines.append(f"עודכן ב- {d}")
                if t:
                    lines.append(f"בשעה - {t}")
                if lines:
                    st.markdown(
                        "<div style='margin-top:-0.35rem; line-height:1.05; font-size:0.85rem; opacity:0.85;'>"
                        + "<br>".join(lines)
                        + "</div>",
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.markdown("### Navigation")

        if hasattr(st, "page_link"):
            def _dot(ok: bool) -> str:
                # Hollow circle vs filled circle (as requested)
                return "●" if ok else "○"

            # Mark completion based on cached payload existence for the current symbol.
            gs_disp = (st.session_state.get("guided_symbol") or default_sym).strip().upper() or default_sym
            sym_eff = resolve_symbol_for_api(gs_disp)

            def _has(key: str) -> bool:
                v = get_cached(sym_eff, api_base, key)
                return isinstance(v, dict) and bool(v)

            def _has_artifact_ok() -> bool:
                art = get_cached(sym_eff, api_base, "analysis_artifact:v1")
                return isinstance(art, dict) and bool(art) and bool(art.get("ok", True))

            st.page_link("app.py", label="Favorite Stocks")

            st.page_link(
                "pages/01_Start_Here.py",
                label=f"{_dot(_has_artifact_ok())} Start Here",
            )
            st.page_link("pages/02_Watchlist.py", label="Watchlist")

            with st.expander("Core lessons", expanded=True):
                st.page_link("pages/03_Charting_Lab.py", label=f"{_dot(_has_artifact_ok())} Charting Lab")
                st.page_link(
                    "pages/04_Fundamentals_Valuation.py",
                    label=f"{_dot(_has_artifact_ok())} Fundamentals Valuation",
                )
                st.page_link(
                    "pages/05_Governance_Sentiment.py",
                    label=f"{_dot(_has_artifact_ok())} Governance Sentiment",
                )
                st.page_link("pages/06_Peer_Comparison.py", label=f"{_dot(_has_artifact_ok())} Peer Comparison")

            with st.expander("Core verdict", expanded=True):
                st.page_link("pages/07_Valuation_Verdict.py", label=f"{_dot(_has_artifact_ok())} Valuation Verdict")
                st.page_link("pages/09_Chart_Technical_Verdict.py", label=f"{_dot(_has_artifact_ok())} Chart Technical Verdict")
                st.page_link("pages/10_Market_Context_Feed.py", label=f"{_dot(_has_artifact_ok())} Market Context Feed")

            st.page_link("pages/08_Stock_360_View.py", label=f"{_dot(_has_artifact_ok())} Stock 360 View")

            st.markdown("<div class='mi-nav-spacer'></div>", unsafe_allow_html=True)
            st.markdown("<div class='mi-nav-green'>More</div>", unsafe_allow_html=True)
            st.page_link("pages/90_Portfolio_Quiz.py", label="Portfolio Quiz")
            st.page_link("pages/91_Macro_Simulation.py", label="Macro Simulation")
            st.page_link("pages/92_Blind_Test.py", label="Blind Test")
            st.page_link("pages/93_Blind_CSV_Import.py", label="Blind CSV (אנונימי)")

            gs = st.session_state.get("guided_symbol", "")
            if is_placeholder_symbol(gs):
                eff = resolve_symbol_for_api(gs)
                st.caption(
                    f"הטיקר `{str(gs).strip().upper() or '—'}` שמור לתרגול/אנונימי — "
                    f"לא נשלח ל-API. הנתונים בלשוניות מבוססים על **{eff}**."
                )
        else:
            st.caption("Update Streamlit to use in-app navigation.")
