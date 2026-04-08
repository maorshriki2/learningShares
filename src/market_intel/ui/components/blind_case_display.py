from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from market_intel.ui.components.cards import metric_card, section_divider, signal_color
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.chart_snapshot_narrative import render_blind_price_snapshot


def render_blind_case_metrics_and_chart(
    study: dict[str, Any],
    *,
    company_label: str,
    show_codename_in_title: bool = True,
) -> None:
    """
    study: same shape as GET /blindtest/{id}/blind (includes financials_summary, price_chart_data).
    company_label: shown as the company name (e.g. codename or 'anony').
    """
    name_part = f"**{company_label}**" if show_codename_in_title else company_label
    st.markdown(f"## חברה: {name_part} | שנה: {study['year']} | סקטור: {study['sector']}")
    st.caption(f"מחיר נקודת ה-snapshot: ${study['price_at_snapshot']:.2f}")

    fin = study.get("financials_summary", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        pe = fin.get("pe_ratio")
        metric_card("P/E", f"{pe:.1f}" if pe else "N/A (הפסד)", badge_color="yellow" if pe else "red")
    with c2:
        roa = (fin.get("net_income_b") or 0) / (fin.get("total_assets_b") or 1) * 100
        metric_card("ROA", f"{roa:.1f}%", badge_color=signal_color(roa, 0, 5))
    with c3:
        dte = fin.get("debt_to_equity")
        metric_card("חוב/הון (D/E)", f"{dte:.1f}x" if dte else "N/A", badge_color=signal_color(-(dte or 0), -3, -0.5))
    with c4:
        ocf = fin.get("operating_cashflow_b")
        metric_card(
            "תזרים תפעולי",
            f"${ocf:+.1f}B" if ocf is not None else "N/A",
            badge_color="green" if ocf and ocf > 0 else "red",
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        piotr = study.get("piotroski_score")
        badge_p = "green" if piotr and piotr >= 7 else ("yellow" if piotr and piotr >= 4 else "red")
        metric_card("Piotroski F", f"{piotr}/9" if piotr is not None else "N/A", badge_color=badge_p)
    with c6:
        z = study.get("altman_z")
        zone = study.get("altman_zone", "grey")
        z_color = "green" if zone == "safe" else ("red" if zone == "danger" else "yellow")
        metric_card("Altman Z", f"{z:.2f}" if z else "N/A", zone, badge_color=z_color)
    with c7:
        rev = fin.get("revenue_b")
        metric_card("הכנסות", f"${rev:.1f}B" if rev else "N/A")
    with c8:
        ni = fin.get("net_income_b")
        metric_card(
            "רווח נקי",
            f"${ni:+.2f}B" if ni is not None else "N/A",
            badge_color="green" if ni and ni > 0 else "red",
        )

    section_divider()
    st.markdown("### 📈 גרף מחיר (יחסי — בלי תאריכים מזהים)")
    chart_data = study.get("price_chart_data", [])
    if chart_data:
        price_snap = study["price_at_snapshot"]
        x_labels = [f"t{d['offset_months']:+d}m" for d in chart_data]
        prices = [round(d["price_factor"] * price_snap, 2) for d in chart_data]
        colors = ["#34d399" if p >= price_snap else "#f87171" for p in prices]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_labels,
                y=prices,
                mode="lines+markers",
                name="מחיר יחסי",
                line=dict(color="#38bdf8", width=2),
                marker=dict(color=colors, size=9),
            )
        )
        fig.add_hline(y=price_snap, line_dash="dot", line_color="rgba(248,248,248,0.25)", annotation_text="Snapshot")
        fig.update_layout(
            template="plotly_dark",
            height=300,
            margin=dict(l=30, r=20, t=20, b=30),
            xaxis_title="תקופה (t=0 = נקודת snapshot)",
            yaxis_title="מחיר ($)",
        )
        st.plotly_chart(fig, use_container_width=True, width="stretch")
        render_chart_reading_guide("blind_price_context")
        render_blind_price_snapshot(chart_data, float(price_snap))
    else:
        st.warning("אין נתוני גרף (price_chart_json ריק או חסר).")
