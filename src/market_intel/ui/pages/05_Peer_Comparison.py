from __future__ import annotations

import math
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.active_recall import render_active_recall_checkpoint
from market_intel.ui.components.cards import inject_card_css, metric_card, section_divider
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.financial_snapshot_narrative import render_peer_snapshot
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.guided_learning import render_guided_learning_sidebar
from market_intel.ui.components.mentor_expander import MENTOR_PEERS, render_mentor
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="השוואת מתחרים", layout="wide")
inject_terminal_theme()
inject_card_css()

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("📊 השוואת מתחרים — Relative Valuation")
render_mentor(MENTOR_PEERS)
render_glossary_terms(["P/E", "EV/EBITDA"])
section_divider()

col_s, col_e = st.columns([2, 3])
symbol = col_s.text_input("סמבול", value=st.session_state.get("guided_symbol", "AAPL")).strip().upper()
extra_input = col_e.text_input(
    "מתחרים נוספים (אופציונלי, מופרד בפסיק)",
    value="",
    placeholder="לדוגמה: GOOGL, AMZN",
)
symbol = render_guided_learning_sidebar("peers", symbol, show_symbol_input=False)

try:
    data = client.peer_comparison(symbol, extra_input)
except Exception as exc:
    st.error(f"שגיאת API: {exc}")
    st.info("בדוק שהאפליקציה רצה: `python scripts/run_app.py` (API + ממשק יחד).")
    st.stop()

rows: list[dict[str, Any]] = data.get("rows", [])
avg: dict[str, Any] = data.get("sector_avg", {})

if not rows:
    st.warning("לא נמצאו נתונים.")
    st.stop()

subject = next((r for r in rows if r.get("is_subject")), rows[0])

st.markdown("### נתוני הנבחרת")
c1, c2, c3, c4 = st.columns(4)
with c1:
    pe = subject.get("pe_ratio")
    avg_pe = avg.get("pe_ratio")
    badge = "green" if pe and avg_pe and pe < avg_pe * 0.9 else ("red" if pe and avg_pe and pe > avg_pe * 1.2 else "yellow")
    metric_card("P/E", f"{pe:.1f}" if pe else "N/A", "מכפיל רווח", badge="זול" if badge == "green" else ("יקר" if badge == "red" else "ממוצע"), badge_color=badge)
with c2:
    ev = subject.get("ev_ebitda")
    metric_card("EV/EBITDA", f"{ev:.1f}" if ev else "N/A", "מכפיל תפעולי")
with c3:
    om = subject.get("operating_margin")
    pct = f"{om * 100:.1f}%" if om else "N/A"
    badge_m = "green" if om and om > 0.20 else ("red" if om and om < 0 else "yellow")
    metric_card("שולי רווח תפעולי", pct, "", badge_color=badge_m)
with c4:
    rg = subject.get("revenue_growth")
    rg_pct = f"{rg * 100:.1f}%" if rg else "N/A"
    metric_card("צמיחת הכנסות", rg_pct, "YoY", badge_color="green" if rg and rg > 0.10 else "yellow")

render_chart_reading_guide(
    "peer_comparison_full",
    expander_title="📖 איך לקרוא מכפילים, טבלה ושורת ממוצע",
)

section_divider()
st.markdown("### טבלת השוואה מלאה")

all_rows = rows + [avg]
display = []
for r in all_rows:
    def _pct(v: Any) -> str:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{float(v) * 100:.1f}%"

    def _round(v: Any, d: int = 1) -> str:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{float(v):.{d}f}"

    def _mcap(v: Any) -> str:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        b = float(v) / 1e9
        return f"${b:.1f}B"

    is_subj = r.get("is_subject", False)
    tag = " ⭐" if is_subj else ""
    display.append(
        {
            "📌 סמבול": r.get("symbol", "") + tag,
            "🏢 שם": r.get("name", ""),
            "💰 שווי שוק": _mcap(r.get("market_cap")),
            "📈 P/E": _round(r.get("pe_ratio")),
            "⚙️ EV/EBITDA": _round(r.get("ev_ebitda")),
            "📐 z(P/E)": _round(r.get("z_pe_ratio"), 2),
            "📐 z(EV/EBITDA)": _round(r.get("z_ev_ebitda"), 2),
            "💹 מרג'ין תפעולי": _pct(r.get("operating_margin")),
            "🚀 צמיחת הכנסות": _pct(r.get("revenue_growth")),
        }
    )

df = pd.DataFrame(display)
st.dataframe(df, width="stretch", hide_index=True)

scatter_pts: list[dict[str, Any]] = []
for r in rows:
    pe = r.get("pe_ratio")
    rg = r.get("revenue_growth")
    if pe is None or rg is None:
        continue
    if isinstance(pe, float) and math.isnan(pe):
        continue
    if isinstance(rg, float) and math.isnan(rg):
        continue
    scatter_pts.append(
        {
            "symbol": r.get("symbol", ""),
            "צמיחת הכנסות %": float(rg) * 100.0,
            "P/E": float(pe),
            "נבחרת": "המניה הנבחרת" if r.get("is_subject") else "מתחרה",
        }
    )
if len(scatter_pts) >= 2:
    st.markdown("### פיזור: צמיחת הכנסות מול P/E")
    st.caption("כל נקודה היא חברה בטבלה; המניה עם הכוכב מודגשת בצבע.")
    sdf = pd.DataFrame(scatter_pts)
    fig = px.scatter(
        sdf,
        x="צמיחת הכנסות %",
        y="P/E",
        color="נבחרת",
        hover_name="symbol",
        color_discrete_map={"המניה הנבחרת": "#00d4aa", "מתחרה": "#6b7a8f"},
        template="plotly_dark",
    )
    fig.update_traces(marker=dict(size=12, opacity=0.85))
    fig.update_layout(height=420, margin=dict(l=40, r=20, t=30, b=40))
    st.plotly_chart(fig, width="stretch")

render_peer_snapshot(rows, subject, avg)

section_divider()
st.markdown("### 🔍 ניתוח אוטומטי")

pe_s = subject.get("pe_ratio")
pe_a = avg.get("pe_ratio")
om_s = subject.get("operating_margin")
om_a = avg.get("operating_margin")

findings: list[str] = []
if pe_s and pe_a:
    diff_pct = (pe_s - pe_a) / pe_a * 100
    if diff_pct < -10:
        findings.append(f"✅ **P/E נמוך מהממוצע ב-{abs(diff_pct):.0f}%** — החברה נסחרת בהנחה ביחס לענף.")
    elif diff_pct > 20:
        findings.append(f"⚠️ **P/E גבוה מהממוצע ב-{diff_pct:.0f}%** — פרמיה ביחס לענף. בדוק אם הצמיחה מצדיקה.")

if om_s and om_a:
    if om_s > om_a * 1.1:
        findings.append(f"✅ **שולי רווח גבוהים מהממוצע** ({om_s*100:.1f}% לעומת {om_a*100:.1f}%) — יעילות תפעולית עדיפה.")
    elif om_s < om_a * 0.8:
        findings.append(f"🔴 **שולי רווח נמוכים מהממוצע** ({om_s*100:.1f}% לעומת {om_a*100:.1f}%) — בחן את מבנה העלויות.")

if pe_s and pe_a and om_s and om_a and pe_s < pe_a and om_s > om_a:
    findings.append("💎 **פנינה אפשרית**: P/E נמוך *ו*מרג'ין גבוה מהממוצע — שילוב נדיר שדורש עיון עמוק!")

if not findings:
    findings.append("ℹ️ אין ממצאים בולטים — החברה נסחרת קרוב לממוצע הענף.")

for f in findings:
    st.markdown(f)

section_divider()
render_active_recall_checkpoint(
    page_key="peers",
    prompt="איזה שילוב יכול לרמוז על הזדמנות תמחור יחסית?",
    choices=[
        "P/E גבוה משמעותית ומרג'ין נמוך",
        "P/E נמוך יחסית ומרג'ין תפעולי גבוה יחסית",
        "P/E גבוה ו-EV/EBITDA גבוה",
        "צמיחה שלילית ומכפיל גבוה",
    ],
    correct_index=1,
    explanation="כאשר החברה יעילה יותר (מרג'ין גבוה) אך נסחרת בזול יחסית (P/E נמוך), ייתכן שיש פער תמחור שכדאי לחקור.",
)
