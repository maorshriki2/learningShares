"""Structured, data-driven detailed report for Start Here (educational; Hebrew UI)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from market_intel.ui.components.chart_snapshot_narrative import render_ohlcv_snapshot_narrative
from market_intel.ui.components.financial_snapshot_narrative import (
    build_fundamentals_narrative_lines,
    render_forensic_analyst_alerts,
    render_fundamentals_snapshot,
    render_peer_snapshot,
)


def _last_number(values: list[Any] | None) -> float | None:
    if not values:
        return None
    for v in reversed(values):
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _fmt_num(v: float | None, digits: int = 2, suffix: str = "") -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}{suffix}"


def collect_transparency_notes(data: dict[str, Any]) -> list[str]:
    """Explicit missing / failed data for the ticker snapshot."""
    notes: list[str] = list(data.get("errors") or [])
    ohlcv = data.get("payload_ohlcv")
    if not ohlcv:
        notes.append("לא נטען מטען OHLCV — אין טכני מפורט.")
    else:
        ind = ohlcv.get("indicators") or {}
        checks = [
            ("rsi14", "RSI(14)"),
            ("macd", "MACD"),
            ("macd_signal", "קו אות MACD"),
            ("vwap", "VWAP (סשן)"),
        ]
        for key, he in checks:
            if _last_number(ind.get(key) if isinstance(ind.get(key), list) else None) is None:
                notes.append(f"אין ערך אחרון זמין ל־{he} (`{key}`).")
        pats = ohlcv.get("patterns") or []
        if not pats:
            notes.append("לא זוהו תבניות בחלון הנרות שנטען (או ריק).")

    fund = data.get("payload_fundamentals")
    if not fund:
        notes.append("לא נטען לוח פונדמנטלים — אין ROIC/DCF/פורנזיקה מפורטים.")
    else:
        if fund.get("roic_latest") is None:
            notes.append("שדה `roic_latest` חסר ב־API.")
        if fund.get("altman_z") is None:
            notes.append("שדה `altman_z` חסר ב־API.")
        if fund.get("margin_of_safety_pct") is None:
            notes.append("שדה `margin_of_safety_pct` (MOS) חסר ב־API.")
        if fund.get("wacc") is None:
            notes.append("שדה `wacc` חסר ב־API.")
        dcf = fund.get("dcf_base")
        if not isinstance(dcf, dict) or dcf.get("intrinsic_per_share") is None:
            notes.append("ערך `dcf_base.intrinsic_per_share` חסר או לא תקין.")

    peers = data.get("payload_peers")
    if not peers:
        notes.append("לא נטענה השוואת מתחרים.")
    else:
        rows = peers.get("rows") or []
        if not next((r for r in rows if r.get("is_subject")), None):
            notes.append("בטבלת המתחרים אין שורת נושא (`is_subject`).")

    macro = data.get("macro")
    if not macro:
        notes.append("לא נטענו שיעורי ריבית (מאקרו).")
    else:
        if macro.get("t10") is None:
            notes.append("שיעור Treasury 10Y חסר.")
        if macro.get("t2") is None:
            notes.append("שיעור Treasury 2Y חסר.")

    return notes


def render_start_here_detailed_report(symbol: str, data: dict[str, Any]) -> None:
    st.subheader("4) דוח מפורט — איך קוראים את הטיקר מהנתונים")
    st.caption(
        "הסעיפים הבאים נבנים **ישירות** משדות ה־API שכבר נמשכו. "
        "זה חומר לימודי — **לא** ייעוץ השקעות ולא תחזית מחיר."
    )

    ohlcv = data.get("payload_ohlcv")
    fund = data.get("payload_fundamentals")
    peers = data.get("payload_peers")
    macro = data.get("macro") or {}

    with st.expander("טכני — אינדיקטורים, תבניות ונרטיב", expanded=False):
        if ohlcv:
            ind = ohlcv.get("indicators") or {}
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("RSI(14) אחרון", _fmt_num(_last_number(ind.get("rsi14")), 1))
            with c2:
                st.metric("MACD", _fmt_num(_last_number(ind.get("macd")), 3))
            with c3:
                st.metric("MACD signal", _fmt_num(_last_number(ind.get("macd_signal")), 3))
            with c4:
                st.metric("MACD hist", _fmt_num(_last_number(ind.get("macd_histogram")), 3))
            c5, c6, c7 = st.columns(3)
            with c5:
                st.metric("VWAP אחרון", _fmt_num(_last_number(ind.get("vwap")), 2))
            with c6:
                st.metric("Ichimoku tenkan", _fmt_num(_last_number(ind.get("ichimoku_tenkan")), 2))
            with c7:
                pats = ohlcv.get("patterns") or []
                st.metric("תבניות שזוהו", str(len(pats)))
            if pats:
                names = [str(p.get("name", "?")) for p in pats[:12]]
                st.markdown("**שמות תבניות (עד 12):** " + ", ".join(names))
            fib = ohlcv.get("fibonacci")
            if isinstance(fib, dict) and fib.get("levels"):
                st.caption(
                    f"Fibonacci: swing high/low — {fib.get('swing_high')} / {fib.get('swing_low')} "
                    f"({fib.get('direction', '')})"
                )
            candles = ohlcv.get("candles") or []
            tf = str(ohlcv.get("timeframe") or "1d")
            render_ohlcv_snapshot_narrative(
                symbol=symbol,
                timeframe=tf,
                candles=candles,
                indicators=ind,
                patterns=pats,
                fibonacci=fib if isinstance(fib, dict) else None,
            )
        else:
            st.warning("אין מטען טכני — לא ניתן להציג פירוט.")

    with st.expander("פונדמנטלים והערכה — שדות מה־API + נרטיב", expanded=False):
        if fund:
            wacc_pct = float(fund.get("wacc") or 0) * 100.0
            st.markdown(
                f"**WACC (מודל):** {_fmt_num(wacc_pct, 2)}% — "
                f"**מחיר שוק:** {_fmt_num(_safe_f(fund.get('market_price')), 2)}"
            )
            dcf = fund.get("dcf_base") if isinstance(fund.get("dcf_base"), dict) else {}
            st.markdown(
                f"**DCF בסיס:** צמיחה גבוהה `{dcf.get('growth_high')}`, "
                f"צמיחה טרמינלית `{dcf.get('terminal_growth')}`, "
                f"intrinsic למניה `{_fmt_num(_safe_f(dcf.get('intrinsic_per_share')), 2)}`, "
                f"EV `{_fmt_num(_safe_f(dcf.get('enterprise_value')), 0)}`."
            )
            st.markdown(
                f"**ROIC אחרון:** {_fmt_num(_safe_f_pct(fund.get('roic_latest')), 2)}% — "
                f"**Piotroski F:** {fund.get('piotroski_score', '—')} — "
                f"**Altman Z:** {_fmt_num(_safe_f(fund.get('altman_z')), 2)} — "
                f"**MOS:** {_fmt_num(_safe_f(fund.get('margin_of_safety_pct')), 1)}%"
            )
            flags = fund.get("piotroski_flags") or {}
            if isinstance(flags, dict) and flags:
                st.markdown("**דגלי Piotroski (מה־API):**")
                st.json(flags)
            sens = fund.get("dcf_sensitivity")
            if isinstance(sens, dict) and sens.get("intrinsic_per_share_matrix"):
                st.markdown(
                    "**רגישות DCF:** מטריצת intrinsic זמינה; "
                    "לפרטים מלאים עברו ל־Fundamentals."
                )
            render_fundamentals_snapshot(fund)
            render_forensic_analyst_alerts(fund)
            with st.expander("שורות נרטיב מלאות (אותו מנגנון כמו בדף הפונדמנטלים)", expanded=False):
                for line in build_fundamentals_narrative_lines(fund):
                    st.markdown(f"- {line}")
        else:
            st.warning("אין לוח פונדמנטלים.")

    with st.expander("מתחרים — יחסים ונרטיב", expanded=False):
        if peers:
            rows = peers.get("rows") or []
            me = next((r for r in rows if r.get("is_subject")), None)
            avg = peers.get("sector_avg") or {}
            if me:
                st.markdown(
                    f"**נושא:** `{me.get('symbol')}` — שם: {me.get('name', '—')}, "
                    f"סקטור: {me.get('sector', '—')}"
                )
                st.markdown(
                    f"P/E **{_fmt_num(_safe_f(me.get('pe_ratio')), 2)}**, "
                    f"EV/EBITDA **{_fmt_num(_safe_f(me.get('ev_ebitda')), 2)}**, "
                    f"מרג’ין תפעולי **{_fmt_num(_safe_f_pct(me.get('operating_margin')), 2)}%**, "
                    f"צמיחת הכנסות **{_fmt_num(_safe_f_pct(me.get('revenue_growth')), 2)}%**."
                )
                zpe = me.get("z_pe_ratio")
                zev = me.get("z_ev_ebitda")
                if zpe is not None or zev is not None:
                    st.caption(f"Z-scores בטבלה: P/E z={zpe}, EV/EBITDA z={zev}")
                render_peer_snapshot(rows, me, avg)
            else:
                st.warning("אין שורת נושא בטבלה.")
        else:
            st.warning("אין נתוני מתחרים.")

    with st.expander("מאקרו — ריבית ועקום", expanded=False):
        if macro:
            st.metric("Treasury 10Y", macro.get("t10", "—"))
            st.metric("Treasury 2Y", macro.get("t2", "—"))
            curve_txt = (
                "הפוך — לרוב סביבה רגישה יותר למכפילים"
                if macro.get("inverted_curve")
                else "לא הפוך"
            )
            st.write(f"**עקום:** {curve_txt}")
        else:
            st.warning("אין נתוני מאקרו.")

    trans = collect_transparency_notes(data)
    with st.expander("שקיפות — מה חסר או נכשל", expanded=True):
        if not trans:
            st.success("אין הערות חסרים מעבר לשגיאות טעינה (אם היו).")
        else:
            for line in trans:
                st.markdown(f"- {line}")

    st.markdown("**המשך מודרך:**")
    if hasattr(st, "page_link"):
        st.page_link("pages/03_Charting_Lab.py", label="Charting Lab", icon="📈")
        st.page_link("pages/04_Fundamentals_Valuation.py", label="Fundamentals", icon="📊")
        st.page_link("pages/06_Peer_Comparison.py", label="Peers", icon="⚖️")
        st.page_link("pages/05_Governance_Sentiment.py", label="Governance", icon="🏛️")
        st.page_link("pages/91_Macro_Simulation.py", label="Macro", icon="🌍")
        st.page_link("pages/90_Portfolio_Quiz.py", label="Portfolio & Quiz", icon="💼")


def _safe_f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _safe_f_pct(x: Any) -> float | None:
    v = _safe_f(x)
    if v is None:
        return None
    return v * 100.0
