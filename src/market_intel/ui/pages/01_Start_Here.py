from __future__ import annotations

from typing import Any

import streamlit as st
from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.explanation_blocks import render_focus_block, render_focus_heading
from market_intel.ui.components.sidebar_nav import render_sidebar_nav
from market_intel.ui.components.start_here_report import render_start_here_detailed_report
from market_intel.ui.state.session import ensure_api_base
from market_intel.ui.state.analysis_cache import require_cached

st.set_page_config(page_title="Start Here", layout="wide")
inject_terminal_theme()
inject_card_css()
render_sidebar_nav("start_here")

base = ensure_api_base()

st.title("🚦 Start Here — מצב למתחילים")
st.caption("2 דקות להבין את החברה: מי היא, מה הסיפור, מה הסיכונים — ואז עוברים לשכבות הנתונים.")

col_main, col_right = st.columns([3.2, 1.1], gap="large")

with col_right:
    render_focus_heading("איך לעבוד עם העמוד הזה", variant="steps")
    render_focus_block(
        "1) בחר סימבול בסיידבר ולחץ **ניתוח** (טעינה פעם אחת ושמירה מקומית).\n"
        "2) קרא את 3 הסעיפים הראשונים כאן.\n"
        "3) קפוץ לדפים למטה לפי הצורך: **Fundamentals**, **Peers**, **Charting**, **Market Context**.",
        variant="steps",
    )
    render_focus_heading("מה *לא* לעשות", variant="caution")
    render_focus_block(
        "לא לקבל החלטה רק על סמך ציון 0–4.\n"
        "המטרה כאן היא **למידה** וסדר מחשבה, לא תחזית.\n"
        "אם חסר מידע (רואים ב«שקיפות» בדוח) — התמונה חלקית.",
        variant="caution",
    )
    render_focus_heading("מה נחשב הצלחה", variant="insight")
    render_focus_block(
        "בסוף העמוד אתה יודע לענות במשפט:\n"
        "מה החברה עושה, מה שני Drivers מרכזיים, ומה שני סיכונים מרכזיים —\n"
        "ורק אז עוברים לשכבות הנתונים.",
        variant="insight",
    )

with col_main:
    symbol = (st.session_state.get("guided_symbol") or "AAPL").strip().upper() or "AAPL"


def _fmt_usd(x: Any) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "לא זמין"
    if v >= 1e12:
        return f"${v/1e12:.2f}T"
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.2f}M"
    return f"${v:,.0f}"


def _company_card(symbol: str) -> None:
    sym = (symbol or "").strip().upper()
    if not sym:
        return
    # Strict mode: never fetch on render; read from Analyze prefetch cache only.
    inst = require_cached(
        sym,
        base,
        "instrument_summary",
        message_he="אין Instrument Summary שמור. לחץ **ניתוח** בסיידבר כדי לטעון הכל פעם אחת.",
    ) or {}

    name = inst.get("name") or "—"
    sector = inst.get("sector") or "—"
    mc = inst.get("market_cap")
    px = inst.get("price")
    beta = inst.get("beta")
    vol = inst.get("volatility_1y")

    st.subheader("0) מי זו החברה — קצר ולעניין")
    st.markdown(f"**{sym} — {name}**")
    st.caption("Beginner: בונים הקשר לפני אינדיקטורים. Advanced: פירוט טכני/שקיפות בהמשך.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sector", str(sector))
    c2.metric("Market cap", _fmt_usd(mc) if mc is not None else "לא זמין")
    c3.metric("Price", f"{float(px):.2f} $" if isinstance(px, (int, float)) else "לא זמין")
    c4.metric("Beta", f"{float(beta):.2f}" if isinstance(beta, (int, float)) else "לא זמין")

    with st.expander("עוד — איך לחשוב על החברה (תמציתי)", expanded=False):
        st.markdown(
            """
**מה עושים כאן?**  
- משפט אחד: מה החברה מוכרת / למי / איך מרוויחה כסף.  
- שתי נקודות “למה עוקבים”: צמיחה, יתרון תחרותי, מוצר מוביל, רגולציה, מחזוריות.  
- שני סיכונים: תחרות, מאקרו, תמחור גבוה, מינוף, תלות בלקוח/ספק.

**נקודות בקרה לדוח הבא (פרקטי):**  
- האם ההכנסות/מרג’ין ממשיכים בכיוון?  
- האם התזה שלך נשברת או מתחזקת?
"""
        )
        if isinstance(vol, (int, float)):
            st.caption(f"Volatility (1Y, מחושב): {float(vol) * 100:.1f}%")


def _last_number(values: list[Any] | None) -> float | None:
    if not values:
        return None
    for v in reversed(values):
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "לא זמין"
    return f"{v:.1f}%"


def _status_chip(ok: bool | None, good: str, bad: str) -> str:
    if ok is None:
        return "🟡 אין מספיק נתונים"
    return f"🟢 {good}" if ok else f"🔴 {bad}"


_company_card(symbol)

st.info("כאן אין כפתור ניתוח מקומי. לחץ **ניתוח** בסיידבר מתחת לסימבול כדי לטעון ולשמור את כל הלשוניות.")

# Central artifact: single source of truth.
artifact = require_cached(
    symbol,
    base,
    "analysis_artifact:v1",
    message_he="אין Artifact שמור ל־Start Here. לחץ **ניתוח** בסיידבר כדי לטעון הכל פעם אחת.",
)
inputs = artifact.get("inputs") if isinstance(artifact, dict) else {}
ohlcv = inputs.get("ohlcv") if isinstance(inputs, dict) else {}
fund = inputs.get("fundamentals") if isinstance(inputs, dict) else {}
peers = inputs.get("peers") if isinstance(inputs, dict) else {}
rates = inputs.get("macro_rates") if isinstance(inputs, dict) else {}

# Build the local view-model (same shape as before).
data: dict[str, Any] = {"symbol": symbol}
errors: list[str] = []

data["payload_ohlcv"] = ohlcv or None
ind = (ohlcv or {}).get("indicators", {}) if isinstance(ohlcv, dict) else {}
rsi = _last_number(ind.get("rsi14")) if isinstance(ind, dict) else None
macd = _last_number(ind.get("macd")) if isinstance(ind, dict) else None
macd_sig = _last_number(ind.get("macd_signal")) if isinstance(ind, dict) else None
pair_ok = macd is not None and macd_sig is not None
patterns = (ohlcv or {}).get("patterns", []) if isinstance(ohlcv, dict) else []
data["technical"] = {
    "rsi": rsi,
    "macd": macd,
    "macd_signal": macd_sig,
    "macd_histogram": _last_number(ind.get("macd_histogram")) if isinstance(ind, dict) else None,
    "vwap": _last_number(ind.get("vwap")) if isinstance(ind, dict) else None,
    "macd_pair_defined": pair_ok,
    "macd_bullish": bool(pair_ok and macd > macd_sig),
    "patterns_count": len(patterns) if isinstance(patterns, list) else 0,
    "pattern_names": [str(p.get("name", "")) for p in patterns[:10] if isinstance(p, dict) and p.get("name")]
    if isinstance(patterns, list)
    else [],
}
if not ohlcv:
    errors.append("נתוני טכני לא זמינים.")

data["payload_fundamentals"] = fund or None
if isinstance(fund, dict) and fund:
    pe_proxy = None
    price = fund.get("market_price")
    dcf = (fund.get("dcf_base") or {}) if isinstance(fund.get("dcf_base"), dict) else (fund.get("dcf_base") or {})
    intrinsic = dcf.get("intrinsic_per_share") if isinstance(dcf, dict) else None
    try:
        if price and intrinsic:
            pe_proxy = float(price) / float(intrinsic) if float(intrinsic) != 0 else None
    except Exception:
        pe_proxy = None
    data["fundamentals"] = {
        "roic": fund.get("roic_latest"),
        "altman_z": fund.get("altman_z"),
        "piotroski": fund.get("piotroski_score"),
        "mos": fund.get("margin_of_safety_pct"),
        "wacc": fund.get("wacc"),
        "price": price,
        "intrinsic": intrinsic,
        "price_to_intrinsic": pe_proxy,
        "forensic_count": len(fund.get("forensic_flags") or []),
    }
else:
    errors.append("נתוני פונדמנטלי לא זמינים.")
    data["fundamentals"] = {}

data["payload_peers"] = peers or None
if isinstance(peers, dict) and peers:
    rows = peers.get("rows", [])
    me = next((r for r in rows if isinstance(r, dict) and r.get("is_subject")), None) if isinstance(rows, list) else None
    avg = peers.get("sector_avg", {}) if isinstance(peers.get("sector_avg"), dict) else {}
    data["peers"] = {
        "pe_ratio": me.get("pe_ratio") if isinstance(me, dict) else None,
        "sector_pe": avg.get("pe_ratio") if isinstance(avg, dict) else None,
        "ev_ebitda": me.get("ev_ebitda") if isinstance(me, dict) else None,
        "operating_margin": me.get("operating_margin") if isinstance(me, dict) else None,
        "sector_om": avg.get("operating_margin") if isinstance(avg, dict) else None,
        "revenue_growth": me.get("revenue_growth") if isinstance(me, dict) else None,
        "z_pe_ratio": me.get("z_pe_ratio") if isinstance(me, dict) else None,
    }
else:
    errors.append("נתוני מתחרים לא זמינים.")
    data["peers"] = {}

if isinstance(rates, dict) and rates:
    data["macro"] = {
        "t10": rates.get("treasury_10y"),
        "t2": rates.get("treasury_2y"),
        "inverted_curve": (rates.get("treasury_2y") or 0) > (rates.get("treasury_10y") or 0),
    }
else:
    errors.append("נתוני ריבית לא זמינים.")
    data["macro"] = {}

data["errors"] = errors

section_divider()
st.subheader("1) מה רואים עכשיו — בשפה פשוטה")

tech = data.get("technical", {})
fund = data.get("fundamentals", {})
peer = data.get("peers", {})
macro = data.get("macro", {})

t1, t2, t3, t4 = st.columns(4)
with t1:
    rsi = tech.get("rsi")
    is_rsi_ok = None if rsi is None else (30 <= rsi <= 70)
    st.markdown(f"**טכני (RSI):** {_fmt_pct(rsi) if rsi is not None else 'לא זמין'}")
    st.caption(_status_chip(is_rsi_ok, "לא קיצוני", "קיצוני — דורש זהירות"))
    if tech.get("macd_pair_defined"):
        st.caption("MACD מעל האות (שורי)" if tech.get("macd_bullish") else "MACD מתחת לאות")
    else:
        st.caption("MACD: אין זוג ערכים אחרון בחלון")
    pc = tech.get("patterns_count")
    st.caption(f"תבניות שזוהו: {pc}" if pc is not None else "תבניות: —")
with t2:
    roic = fund.get("roic")
    roic_pct = float(roic) * 100 if isinstance(roic, (int, float)) else None
    is_roic_ok = None if roic_pct is None else roic_pct >= 10
    st.markdown(f"**איכות עסק (ROIC):** {_fmt_pct(roic_pct)}")
    st.caption(_status_chip(is_roic_ok, "איכות טובה", "איכות בינונית/חלשה"))
with t3:
    pe = peer.get("pe_ratio")
    spe = peer.get("sector_pe")
    rel_ok = None if pe is None or spe is None else pe <= spe
    if isinstance(pe, (int, float)):
        st.markdown(f"**תמחור יחסי (P/E):** {pe:.1f}")
    else:
        st.markdown("**תמחור יחסי (P/E):** לא זמין")
    st.caption(_status_chip(rel_ok, "זול/דומה לענף", "יקר מהענף"))
with t4:
    inv = macro.get("inverted_curve")
    st.markdown(f"**סביבת ריבית (10Y):** {macro.get('t10', 'לא זמין')}")
    st.caption(_status_chip(False if inv else True, "סביבת ריבית רגילה", "עקום הפוך — שוק רגיש"))

section_divider()
st.subheader("2) מה זה אומר בפועל")

score = 0
notes: list[str] = []

if tech.get("rsi") is not None:
    if 35 <= float(tech["rsi"]) <= 65:
        score += 1
        notes.append("המומנטום לא קיצוני כרגע (RSI מאוזן).")
    else:
        notes.append("המומנטום קיצוני יחסית — להימנע מהחלטה מהירה.")

if isinstance(fund.get("roic"), (int, float)):
    if float(fund["roic"]) >= 0.10:
        score += 1
        notes.append("החברה יעילה תפעולית (ROIC טוב).")
    else:
        notes.append("ROIC נמוך — איכות העסק פחות חזקה.")

if isinstance(peer.get("pe_ratio"), (int, float)) and isinstance(
    peer.get("sector_pe"), (int, float)
):
    if float(peer["pe_ratio"]) <= float(peer["sector_pe"]):
        score += 1
        notes.append("התמחור מול מתחרים סביר/נוח.")
    else:
        notes.append("התמחור מול מתחרים יקר יחסית.")

if macro.get("inverted_curve") is False:
    score += 1
    notes.append("סביבת המאקרו פחות לוחצת כרגע.")
elif macro.get("inverted_curve") is True:
    notes.append("עקום הפוך: לדרוש מרווח ביטחון גדול יותר.")

for n in notes:
    st.write(f"- {n}")

section_divider()
st.subheader("3) מסקנה מהירה + מה לעשות עכשיו")
if score >= 3:
    st.success("תמונה כללית חיובית לפי ארבעת השכבות. כדאי להעמיק בדוח המפורט למטה.")
elif score == 2:
    st.warning("תמונה מעורבת. השלימו פערים בדוח המפורט ובדפי Fundamentals + Peers.")
else:
    st.error("כרגע האות החזק פחות ברור. בדקו מה חסר בדוח השקיפות למטה.")

with st.expander("איך חושב הציון (0–4)", expanded=False):
    st.markdown(
        """
- **+1 טכני:** RSI בין 35 ל־65 (פחות קיצון).
- **+1 איכות:** ROIC ≥ 10%.
- **+1 יחסי:** P/E הנושא ≤ ממוצע הענף בטבלה.
- **+1 מאקרו:** עקום תשואות לא הפוך.

ציון גבוה לא אומר «קנו» — רק שהשכבות מתיישרות בכיוון פחות עוין בפריים הלימודי.
"""
    )

st.markdown("**הצעד הבא:** פתחו את **הדוח המפורט** בסעיף 4, או את **מסלול האנליסט** מהקישורים שם.")

render_start_here_detailed_report(symbol, data)

if data.get("errors"):
    section_divider()
    st.info("חלק מהמקורות לא נטענו — ראו גם «שקיפות — מה חסר» בדוח המפורט.")
    for err in data["errors"]:
        st.caption(f"- {err}")

st.caption("לא ייעוץ השקעות; חומר לימודי בלבד.")
