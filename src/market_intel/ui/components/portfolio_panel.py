from __future__ import annotations

from typing import Any

import streamlit as st


def render_portfolio(snapshot: dict[str, Any]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"${float(snapshot.get('cash_usd', 0)):,.2f}")
    c2.metric("Equity", f"${float(snapshot.get('total_equity', 0)):,.2f}")
    c3.metric("Unrealized P&L", f"${float(snapshot.get('unrealized_pnl', 0)):,.2f}")
    c4.metric("Portfolio beta (approx)", f"{float(snapshot.get('portfolio_beta', 1.0)):.2f}")

    st.subheader("Positions")
    for p in snapshot.get("positions", []) or []:
        st.write(
            f"{p.get('symbol')} | qty {p.get('quantity'):,.4f} | "
            f"avg {p.get('avg_cost'):.2f} | last {p.get('last_price')} | "
            f"mv {p.get('market_value')} | uPnL {p.get('unrealized_pnl')}"
        )

    st.subheader("Sector weights")
    sw = snapshot.get("sector_weights") or {}
    for k, v in sw.items():
        st.progress(min(float(v), 1.0), text=f"{k}: {float(v)*100:.1f}%")
