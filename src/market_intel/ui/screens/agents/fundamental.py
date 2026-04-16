from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from market_intel.modules.fundamentals.education.dcf_explainer import margin_of_safety_note
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import section_divider
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.dcf_sliders import dcf_controls
from market_intel.ui.components.explanation_blocks import formula_row, render_focus_block
from market_intel.ui.components.financial_snapshot_narrative import (
    render_forensic_analyst_alerts,
    render_fundamentals_snapshot,
)
from market_intel.ui.components.fundamentals_tables import statements_tabs
from market_intel.ui.components.glossary import render_glossary_terms
from market_intel.ui.components.mentor_expander import MENTOR_FUNDAMENTALS, render_mentor
from market_intel.ui.formatters.bidi_text import ltr_embed as L
from market_intel.ui.formatters.bidi_text import md_code as C
from market_intel.ui.formatters.usd_compact import format_usd_compact
from market_intel.ui.state.analysis_cache import require_cached
from market_intel.ui.state.session import ensure_api_base


def render() -> None:
    base = ensure_api_base()
    client = MarketIntelApiClient(base)

    st.title("📋 Fundamentals & Valuation — ניתוח פונדמנטלי")
    render_mentor(MENTOR_FUNDAMENTALS)
    render_glossary_terms(["P/E", "ROIC", "WACC"])
    section_divider()
    st.info(
        "מה עושים פה ב‑30 שניות: "
        "1) איכות (ROIC מול WACC) 2) יציבות/שיפור (Piotroski) 3) הערכה (DCF+MOS) "
        "4) אימות בדוחות. "
        "Beginner קצר כאן; Advanced בהרחבות."
    )
    symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"

    artifact = require_cached(
        symbol,
        base,
        "analysis_artifact:v1",
        message_he="אין Artifact שמור. לחץ **ניתוח** בסיידבר מתחת לסימבול כדי לטעון הכל פעם אחת.",
    )
    inputs = artifact.get("inputs") if isinstance(artifact, dict) else {}
    dash = inputs.get("fundamentals") if isinstance(inputs, dict) else {}

    def _usd_kpi(key: str) -> str:
        v = dash.get(key)
        if v is None:
            return "n/a"
        try:
            return format_usd_compact(float(v))
        except (TypeError, ValueError):
            return "n/a"

    st.markdown("##### מדדי מודל + דוח הכנסות (שנה אחרונה)")
    _kfy = dash.get("kpi_fiscal_year")
    if _kfy is not None:
        st.caption(
            f"סכומים בדולרים (**{L('USD')}**) בפורמט מקוצר; לפי שנה **{_kfy}** מהטבלאות למטה."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{L('WACC')} (מודל)", f"{float(dash.get('wacc', 0)) * 100:.2f}%")
    if dash.get("roic_latest") is not None:
        c2.metric(f"{L('ROIC')} (אחרון)", f"{float(dash['roic_latest']) * 100:.2f}%")
    else:
        c2.metric(f"{L('ROIC')} (אחרון)", "n/a")
    _piot = dash.get("piotroski_score")
    c3.metric(f"{L('Piotroski')} F", str(_piot) if _piot is not None else "n/a")
    _mp = dash.get("market_price")
    c4.metric(
        "מחיר שוק (עזר)",
        f"{float(_mp):.2f} $" if _mp is not None else "n/a",
    )

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric(L("Revenue"), _usd_kpi("revenue_latest_usd"))
    r2.metric(L("Gross Profit"), _usd_kpi("gross_profit_latest_usd"))
    r3.metric(L("Operating Income"), _usd_kpi("operating_income_latest_usd"))
    r4.metric(L("EBITDA"), _usd_kpi("ebitda_latest_usd"))
    r5.metric(L("Net Income"), _usd_kpi("net_income_latest_usd"))

    with st.expander(
        f"{L('Altman Z')} — מדד מצוקה (הקשר למניות גדולות)",
        expanded=False,
    ):
        render_focus_block(
            f"**החלטת מוצר:** **{C('Altman Z')}** נבנה במקור ל**תעשייה מייצרת** "
            f"ול**חברות קטנות־בינוניות**.\n\n"
            "אצל **מניות גדולות** הוא לעיתים **פחות רלוונטי** כמדד מדויק —\n"
            "אבל עדיין **דגל גס** למינוף, מבנה מאזן ולחץ חשבונאי,\n"
            "**בלי** לפרש אותו כסיכון פשיטות מדעי.\n\n"
            f"למידה: **מתחת ל־{C('1.81')}** מסמנים לרוב **אזור סיכון מוגבר** במודל הקלאסי —\n"
            "לא אבחנה ולא תחליף לניתוח חוב.",
            variant="neutral",
        )
        _az = dash.get("altman_z")
        if _az is not None:
            st.metric(f"{L('Altman Z')} (מחושב)", f"{float(_az):.2f}")
        else:
            st.caption("לא חושב / אין נתונים מספיקים.")

    render_forensic_analyst_alerts(dash)

    render_chart_reading_guide(
        "fundamentals_kpis_dcf",
        expander_title=f"📖 איך לקרוא את המדדים, את {L('WACC')} ואת {L('DCF')}",
    )
    render_fundamentals_snapshot(dash)

    sens = dash.get("dcf_sensitivity")
    if isinstance(sens, dict) and sens.get("intrinsic_per_share_matrix"):
        st.subheader(f"🧮 מטריצת רגישות {L('DCF')} (בדיקת לחץ)")
        st.caption(
            f"מחיר הוגן למניה לפי מודל {L('DCF')} פנימי. **{L('WACC')}** בטווח ±2 נק׳ אחוז; "
            f"**{L('Terminal growth')}** בטווח ±1 נק׳ אחוז. "
            "צבעים: ירוק = שווי מודל גבוה יותר; אדום = נמוך יותר."
        )
        zmat = sens["intrinsic_per_share_matrix"]
        w_axis = sens.get("wacc_values") or []
        t_axis = sens.get("terminal_growth_values") or []
        x_labels = [f"{float(t) * 100:.2f}%" for t in t_axis]
        y_labels = [f"{float(w) * 100:.2f}%" for w in w_axis]
        z_num: list[list[float | None]] = []
        text_m: list[list[str]] = []
        for row in zmat:
            zr: list[float | None] = []
            tr: list[str] = []
            for cell in row:
                if cell is None:
                    zr.append(float("nan"))
                    tr.append("—")
                else:
                    fv = float(cell)
                    zr.append(fv)
                    tr.append(f"{fv:.1f}")
            z_num.append(zr)
            text_m.append(tr)
        mp = dash.get("market_price")
        zmid_val = None
        if mp is not None and isinstance(mp, (int, float)) and math.isfinite(float(mp)):
            zmid_val = float(mp)
        fig_h = go.Figure(
            data=go.Heatmap(
                z=z_num,
                x=x_labels,
                y=y_labels,
                text=text_m,
                texttemplate="%{text}",
                colorscale="RdYlGn",
                zmid=zmid_val,
                colorbar=dict(title=f"{L('USD')}/{L('share')}"),
            )
        )
        fig_h.update_layout(
            template="plotly_dark",
            height=420,
            xaxis_title=f"{L('Terminal growth')} (טור)",
            yaxis_title=f"{L('WACC')} (שורה)",
            margin=dict(l=60, r=20, t=40, b=60),
        )
        if mp is not None and math.isfinite(float(mp)):
            mps = float(mp)
            st.caption(
                f"מחיר שוק נוכחי (השוואה): **{mps:.2f}** — "
                "תאים עם שווי מודל גבוה ממנו: לרוב «זול יחסית למודל»; נמוך ממנו: «יקר יחסית»."
            )
        st.plotly_chart(fig_h, use_container_width=True, width="stretch")

    st.subheader(f"דוחות כספיים — {L('SEC')} {L('XBRL')} (company facts)")
    statements_tabs(dash)
    render_chart_reading_guide(
        "fundamentals_statements",
        expander_title=(f"📖 איך לקרוא את הטאבים {L('Income')}, {L('Balance Sheet')} ו־ {L('Cash Flow')}"),
    )

    st.subheader(f"{L('Interactive DCF')}")
    _dcf_expl = (
        "**מה זה עושה כאן?** שלושת הסליידרים "
        f"{C('st.slider')} שולחים ל־{C('API')} תרחיש {C('DCF')}.\n\n"
        f"{formula_row('POST /api/v1/fundamentals/{symbol}/dcf/scenario')}\n\n"
        f"שם מועברות שלוש ההנחות: צמיחה בשלב המפורש, {C('Terminal growth')}, ו־{C('WACC')}.\n\n"
        f"השרת מריץ {C('discounted_cash_flow_value')} על **תזרים מזומן חופשי** מהדשבורד (קירוב), "
        "ומחזיר **שווי עסק** ו־**מחיר הוגן למניה** — **רגישות** למודל, לא «מחיר אמת».\n\n"
        "**מתי להזיז כל סליידר (לימודית):**\n\n"
        f"– **צמיחה בשלב {C('1–5')}** — תרחיש שורי/דובי על {C('FCF')} / הכנסות בטווח קצר־בינוני.\n\n"
        f"– **{C('Terminal growth')}** — אופטימיות על צמיחה לנצח; "
        f"חייבת להישאר **מתחת** ל־{C('WACC')}.\n\n"
        f"– **{C('WACC')}** — סיכון / תשואה נדרשת; **עלייה** ב־{C('WACC')} "
        "בדרך כלל **מורידה** שווי נוכחי.\n\n"
        f"**מה לבדוק:** {C('intrinsic_per_share')} מול מחיר השוק; "
        f"כיוון השינוי כשמעלים {C('WACC')} או צמיחה.\n\n"
        f"**מגבלה:** ב־{C('endpoint')} הזה {C('net_debt')} מפושט ל־{C('0')} — "
        "השוואה לדשבורד מלא עלולה להסטה.\n\n"
        f"**למה זה חשוב:** אחריות על הנחות המודל ({C('model governance')}) — "
        "לא לייחס לתוצאה **דיוק סטטיסטי**."
    )
    render_focus_block(_dcf_expl, variant="neutral")
    growth, terminal, wacc = dcf_controls()
    if st.button("חשב מחדש תרחיש DCF"):
        try:
            scenario = client.dcf_scenario(symbol, growth, terminal, wacc)
            st.success(scenario.get("summary", ""))
            st.write(
                {
                    "enterprise_value": scenario.get("enterprise_value"),
                    "intrinsic_per_share": scenario.get("intrinsic_per_share"),
                }
            )
            st.info(scenario.get("margin_of_safety_note", margin_of_safety_note()))
        except Exception as exc:
            st.error(str(exc))

    with st.expander("Margin of safety — הערה קצרה"):
        st.write(margin_of_safety_note())

