from __future__ import annotations

import streamlit as st


def inject_card_css() -> None:
    st.markdown(
        """
<style>
.mi-card {
    background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(12,18,35,0.98));
    border: 1px solid rgba(56,189,248,0.22);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin: 0.4rem 0;
    box-shadow: 0 4px 18px rgba(0,0,0,0.38);
}
.mi-card-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.09em;
    color: #7dd3fc;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}
.mi-card-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: #e2e8f0;
}
.mi-card-sub {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 0.15rem;
}
.mi-badge-green  { background:#064e3b; color:#34d399; border-radius:6px; padding:2px 8px; font-size:0.78rem; }
.mi-badge-red    { background:#450a0a; color:#f87171; border-radius:6px; padding:2px 8px; font-size:0.78rem; }
.mi-badge-yellow { background:#422006; color:#fbbf24; border-radius:6px; padding:2px 8px; font-size:0.78rem; }
.mi-badge-blue   { background:#0c1a36; color:#93c5fd; border-radius:6px; padding:2px 8px; font-size:0.78rem; }
.mi-divider { border:none; border-top:1px solid rgba(56,189,248,0.12); margin:0.8rem 0; }
.mi-table th { color:#7dd3fc !important; font-size:0.78rem; }
.stDataFrame { border-radius:10px !important; overflow:hidden; }
</style>
""",
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str,
    subtitle: str = "",
    badge: str | None = None,
    badge_color: str = "blue",
) -> None:
    badge_html = ""
    if badge:
        badge_html = f'<span class="mi-badge-{badge_color}">{badge}</span>'
    st.markdown(
        f"""
<div class="mi-card">
  <div class="mi-card-header">{label}</div>
  <div class="mi-card-value">{value} {badge_html}</div>
  {"<div class='mi-card-sub'>" + subtitle + "</div>" if subtitle else ""}
</div>""",
        unsafe_allow_html=True,
    )


def section_divider() -> None:
    st.markdown('<hr class="mi-divider">', unsafe_allow_html=True)


def color_badge(text: str, color: str = "blue") -> str:
    return f'<span class="mi-badge-{color}">{text}</span>'


def signal_color(value: float, low: float, high: float) -> str:
    if value <= low:
        return "red"
    if value >= high:
        return "green"
    return "yellow"
