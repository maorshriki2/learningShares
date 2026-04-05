from __future__ import annotations

from typing import Any

import streamlit as st


def render_governance(payload: dict[str, Any]) -> None:
    st.subheader("8-K filings")
    for f in payload.get("filings_8k", [])[:10]:
        st.write(f"{f.get('filed')} — {f.get('form')} — {f.get('url') or ''}")

    st.subheader("Insider activity (Form 4)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Buys", payload.get("insider_summary_buy", 0))
    c2.metric("Sells", payload.get("insider_summary_sell", 0))
    c3.metric("Net shares", f"{payload.get('insider_net_shares', 0):,.0f}")

    for r in payload.get("insider_rows", [])[:12]:
        sh = float(r.get("shares") or 0.0)
        st.caption(
            f"{r.get('transaction_date')} | {r.get('insider_name')} | "
            f"{r.get('transaction_type')} | {sh:,.0f} sh"
        )

    st.subheader("Leadership (yfinance profile)")
    for e in payload.get("executives", [])[:6]:
        st.write(f"**{e.get('name')}** — {e.get('title')} — comp: {e.get('total_comp_usd')}")
