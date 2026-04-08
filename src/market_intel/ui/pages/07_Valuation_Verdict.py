from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import httpx
import plotly.graph_objects as go
import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.chart_reading_guide import render_chart_reading_guide
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.formatters.bidi_text import md_code as _C
from market_intel.ui.state.session import ensure_api_base
from market_intel.ui.state.analysis_cache import require_cached

st.set_page_config(page_title="Valuation Verdict", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("valuation_verdict")

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("💰 Valuation Verdict — DCF/WACC (שקוף)")
st.caption("פסק דין קצר (Buy/Hold/Sell) + Explain מלא: הנחות, רגישות, sanity checks. לא ייעוץ השקעות.")
section_divider()

# #region agent log
def _dbg(hypothesis_id: str, message: str, data: dict[str, Any]) -> None:
    try:
        log_path = Path(r"c:\Projects\learn_shares\debug-a73902.log")
        payload = {
            "sessionId": "a73902",
            "runId": str(st.session_state.get("_valuation_run_id") or "pre"),
            "hypothesisId": hypothesis_id,
            "location": "ui/pages/07_Valuation_Verdict.py",
            "message": message,
            "data": data,
            "timestamp": int(__import__("time").time() * 1000),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _openapi_has_valuation_route(api_base: str) -> dict[str, Any]:
    try:
        with httpx.Client(base_url=api_base, timeout=10.0) as c:
            r = c.get("/openapi.json")
            if not (200 <= r.status_code < 300):
                return {"ok": False, "status_code": r.status_code}
            body = r.json()
            paths = body.get("paths") if isinstance(body, dict) else None
            if not isinstance(paths, dict):
                return {"ok": False, "error": "no_paths"}
            return {
                "ok": True,
                "has_valuation_verdict": "/api/v1/valuation/{symbol}/verdict" in set(paths.keys()),
                "n_paths": len(paths),
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

# #endregion


def _to_f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _fmt_usd(x: Any, digits: int = 2) -> str:
    v = _to_f(x)
    if v is None:
        return "—"
    return f"${v:,.{digits}f}"


def _fmt_pct01(x: Any, digits: int = 1) -> str:
    v = _to_f(x)
    if v is None:
        return "—"
    return f"{v*100:.{digits}f}%"


def _badge(label: str) -> tuple[str, str]:
    l = (label or "").lower()
    if l == "buy":
        return ("BUY", "green")
    if l == "sell":
        return ("SELL", "red")
    return ("HOLD", "yellow")


symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"
st.session_state["_valuation_run_id"] = str(st.session_state.get("_valuation_run_id") or "pre")

col_a, col_b, col_c, col_d = st.columns([1.2, 1.2, 1.2, 2.4])
years = col_a.number_input("Years (fundamentals)", min_value=3, max_value=20, value=10, step=1)
mos_required = col_b.slider("MOS required", min_value=0.0, max_value=0.5, value=0.15, step=0.01)
premium_threshold = col_c.slider("Premium threshold", min_value=0.0, max_value=0.5, value=0.15, step=0.01)
include_explain = col_d.toggle("Include explain", value=True)

col_e, col_f, col_g = st.columns([1.2, 1.2, 2.6])
wacc_span = col_e.slider("WACC span (±)", min_value=0.0, max_value=0.10, value=0.02, step=0.005)
terminal_span = col_f.slider("Terminal g span (±)", min_value=0.0, max_value=0.05, value=0.01, step=0.0025)
grid_size = col_g.selectbox("Sensitivity grid size", options=[3, 5, 7, 9], index=1)

section_divider()
st.info(
    "מה עושים פה ב‑30 שניות: "
    "1) רואים Verdict 2) מסתכלים על MOS ומחיר כניסה 3) בודקים אם המסקנה יציבה במטריצת הרגישות. "
    "אם ה‑Terminal שולט מדי — זה Warning."
)

st.info("ה‑Verdict נטען רק דרך כפתור **ניתוח** בסיידבר (למניעת טעינות חוזרות).")

artifact = require_cached(
    symbol,
    base,
    "analysis_artifact:v1",
    message_he="אין Artifact שמור. לחץ **ניתוח** בסיידבר כדי לטעון את כל הטאבים פעם אחת.",
)
meta = artifact.get("meta") if isinstance(artifact, dict) else {}
cfg = meta.get("config") if isinstance(meta, dict) else {}
v_cfg = (cfg.get("valuation") if isinstance(cfg, dict) else None) if isinstance(cfg, dict) else None
if isinstance(v_cfg, dict):
    st.caption(
        f"Artifact valuation params: MOS={float(v_cfg.get('mos_required') or 0.15):.2f}, "
        f"premium={float(v_cfg.get('premium_threshold') or 0.15):.2f}, "
        f"wacc_span={float(v_cfg.get('wacc_span') or 0.02):.3f}, "
        f"terminal_span={float(v_cfg.get('terminal_span') or 0.01):.4f}, "
        f"grid={int(v_cfg.get('grid_size') or 5)}. "
        "Change in sidebar and click Analyze to recompute."
    )
verdicts = artifact.get("verdicts") if isinstance(artifact, dict) else {}
res = verdicts.get("valuation_verdict") if isinstance(verdicts, dict) else {}
if not isinstance(res, dict) or not res:
    st.info("אין Valuation Verdict בתוך ה־Artifact.")
    st.stop()

if not res.get("ok", False):
    st.error(res.get("message") or "Valuation failed.")
    st.json(res)
    st.stop()

verdict = res.get("verdict") or {}
checks = res.get("sanity_checks") or {}
ranges = res.get("ranges") or {}

lab, color = _badge(str(verdict.get("label") or "hold"))
v1, v2, v3, v4, v5 = st.columns([1.2, 1.4, 1.2, 1.6, 1.2])
v1.metric("Verdict", lab)
v2.metric("מחיר נוכחי", _fmt_usd(verdict.get("current_price")))
v3.metric("Intrinsic (Base)", _fmt_usd(verdict.get("intrinsic_per_share_base")))
v4.metric("מחיר כניסה מומלץ", _fmt_usd(verdict.get("required_entry_price")))
v5.metric("MOS", _fmt_pct01(verdict.get("mos_pct"), 1))

_mos_frac = _to_f(verdict.get("mos_pct"))
if _mos_frac is not None and _mos_frac <= -0.5:
    # st.warning/st.info do not support raw HTML; use markdown + md_code (<bdi>) for RTL/LTR copy.
    _extreme_note = (
        f"<strong>הערה:</strong> פער קיצוני בין מחיר השוק למודל ה־{_C('DCF')}. "
        "חברות צמיחה מואצת או מניות «סיפור» מתומחרות לרוב על בסיס ציפיות עתידיות ספקולטיביות "
        f"(כמו {_C('AI')} או טכנולוגיה חדשה) שאינן משתקפות בתזרימי המזומנים הנוכחיים "
        "של מודל הערכת שווי מסורתי."
    )
    st.markdown(
        f'<div style="direction:rtl;text-align:right;padding:0.75rem 1rem;margin:0.5rem 0;'
        f"background-color:rgba(255,152,0,0.18);border-radius:0.35rem;"
        f'border-inline-start:4px solid #ff9800;">{_extreme_note}</div>',
        unsafe_allow_html=True,
    )

reasons = verdict.get("reasons") or []
if isinstance(reasons, list) and reasons:
    with st.expander("למה יצא ה‑Verdict הזה? (חוקים שהופעלו)", expanded=True):
        for r in reasons:
            st.markdown(f"- {r}")

section_divider()
st.subheader("טווחי שווי (מהרגישות)")
st.caption("P10/P50/P90 מחושבים על כל התאים התקינים במטריצה (מתעלמים מ‑tg>=WACC).")
t1, t2, t3 = st.columns(3)
t1.metric("P10", _fmt_usd(ranges.get("p10")))
t2.metric("P50", _fmt_usd(ranges.get("p50")))
t3.metric("P90", _fmt_usd(ranges.get("p90")))

tw = _to_f(checks.get("terminal_weight_pct"))
tw_flag = str(checks.get("terminal_weight_flag") or "ok")
if tw is not None:
    msg = f"Terminal weight: {tw*100:.1f}% (flag={tw_flag})"
    if tw_flag == "warn":
        st.warning(msg)
    else:
        st.info(msg)

render_chart_reading_guide(
    "valuation_verdict",
    expander_title="📖 איך לקרוא את ה‑Verdict וה‑MOS (Beginner/Advanced)",
)

section_divider()
st.subheader("מטריצת רגישות (WACC × Terminal growth)")
ex = res.get("explain") if isinstance(res.get("explain"), dict) else None
sens = (ex or {}).get("sensitivity") if isinstance(ex, dict) else None
if isinstance(sens, dict):
    w_vals = sens.get("wacc_values") or []
    t_vals = sens.get("terminal_growth_values") or []
    mat = sens.get("intrinsic_per_share_matrix") or []
    if isinstance(w_vals, list) and isinstance(t_vals, list) and isinstance(mat, list) and mat:
        x_labels = [f"{_to_f(t)*100:.2f}%" if _to_f(t) is not None else "—" for t in t_vals]
        y_labels = [f"{_to_f(w)*100:.2f}%" if _to_f(w) is not None else "—" for w in w_vals]
        z: list[list[float]] = []
        text: list[list[str]] = []
        for row in mat:
            zr: list[float] = []
            tr: list[str] = []
            if not isinstance(row, list):
                continue
            for cell in row:
                v = _to_f(cell)
                if v is None:
                    zr.append(float("nan"))
                    tr.append("—")
                else:
                    zr.append(v)
                    tr.append(f"{v:.1f}")
            z.append(zr)
            text.append(tr)

        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=x_labels,
                y=y_labels,
                text=text,
                texttemplate="%{text}",
                colorscale="RdYlGn",
                colorbar=dict(title="$/share"),
            )
        )
        fig.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=60, r=20, t=30, b=60),
            xaxis_title="Terminal growth",
            yaxis_title="WACC",
        )
        st.plotly_chart(fig, use_container_width=True, width="stretch")
    else:
        st.info("אין מטריצת רגישות זמינה.")
else:
    st.info("הפעל Include explain כדי לראות מטריצת רגישות.")

if include_explain and isinstance(ex, dict):
    with st.expander("Explain שקוף (raw)", expanded=False):
        st.json(ex)

st.caption("Educational only — not investment advice.")

