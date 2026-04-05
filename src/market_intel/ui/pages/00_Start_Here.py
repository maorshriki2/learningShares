from __future__ import annotations

from typing import Any

import streamlit as st

from market_intel.ui.bootstrap import inject_terminal_theme
from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.components.cards import inject_card_css, section_divider
from market_intel.ui.components.guided_learning import render_guided_learning_sidebar
from market_intel.ui.state.session import ensure_api_base

st.set_page_config(page_title="Start Here", layout="wide")
inject_terminal_theme()
inject_card_css()

base = ensure_api_base()
client = MarketIntelApiClient(base)

st.title("🚦 Start Here — מצב למתחילים")
st.caption("מסך אחד פשוט: מה רואים, מה זה אומר, ומה עושים עכשיו.")

symbol = st.text_input(
    "בחר מניה להתחלה",
    value=st.session_state.get("start_here_symbol_input", st.session_state.get("guided_symbol", "AAPL")),
    key="start_here_symbol_input",
).upper()
st.session_state["guided_symbol"] = symbol
render_guided_learning_sidebar("charting", symbol, show_symbol_input=False)


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


col_btn, col_info = st.columns([1, 3])
refresh = col_btn.button("נתח עכשיו", type="primary")
col_info.info("המערכת תבדוק טכני + פונדמנטלי + מתחרים + ריבית ותחזיר מסקנה פשוטה.")

last_symbol = st.session_state.get("start_here_symbol")
symbol_changed = last_symbol != symbol
if refresh or symbol_changed or "start_here_data" not in st.session_state:
    data: dict[str, Any] = {"symbol": symbol}
    errors: list[str] = []

    try:
        ohlcv = client.ohlcv(symbol, timeframe="1d", limit=220)
        ind = ohlcv.get("indicators", {})
        rsi = _last_number(ind.get("rsi14"))
        macd = _last_number(ind.get("macd"))
        macd_sig = _last_number(ind.get("macd_signal"))
        patterns = ohlcv.get("patterns", [])
        data["technical"] = {
            "rsi": rsi,
            "macd_bullish": (macd is not None and macd_sig is not None and macd > macd_sig),
            "patterns_count": len(patterns),
        }
    except Exception as exc:
        errors.append(f"נתוני טכני לא זמינים: {exc}")

    try:
        f = client.fundamentals_dashboard(symbol, years=10)
        pe_proxy = None
        price = f.get("market_price")
        dcf = (f.get("dcf_base") or {})
        intrinsic = dcf.get("intrinsic_per_share")
        if price and intrinsic:
            pe_proxy = float(price) / float(intrinsic) if float(intrinsic) != 0 else None
        data["fundamentals"] = {
            "roic": f.get("roic_latest"),
            "altman_z": f.get("altman_z"),
            "piotroski": f.get("piotroski_score"),
            "mos": f.get("margin_of_safety_pct"),
            "price": price,
            "intrinsic": intrinsic,
            "price_to_intrinsic": pe_proxy,
        }
    except Exception as exc:
        errors.append(f"נתוני פונדמנטלי לא זמינים: {exc}")

    try:
        peers = client.peer_comparison(symbol, "")
        rows = peers.get("rows", [])
        me = next((r for r in rows if r.get("is_subject")), None)
        avg = peers.get("sector_avg", {})
        data["peers"] = {
            "pe_ratio": me.get("pe_ratio") if me else None,
            "sector_pe": avg.get("pe_ratio"),
            "ev_ebitda": me.get("ev_ebitda") if me else None,
        }
    except Exception as exc:
        errors.append(f"נתוני מתחרים לא זמינים: {exc}")

    try:
        rates = client.macro_rates()
        data["macro"] = {
            "t10": rates.get("treasury_10y"),
            "t2": rates.get("treasury_2y"),
            "inverted_curve": (rates.get("treasury_2y") or 0) > (rates.get("treasury_10y") or 0),
        }
    except Exception as exc:
        errors.append(f"נתוני ריבית לא זמינים: {exc}")

    data["errors"] = errors
    st.session_state.start_here_data = data
    st.session_state.start_here_symbol = symbol

data = st.session_state.start_here_data

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
    st.markdown(f"**תמחור יחסי (P/E):** {pe:.1f}" if isinstance(pe, (int, float)) else "**תמחור יחסי (P/E):** לא זמין")
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

if isinstance(peer.get("pe_ratio"), (int, float)) and isinstance(peer.get("sector_pe"), (int, float)):
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
st.subheader("3) מסקנה פשוטה + מה לעשות עכשיו")
if score >= 3:
    st.success("תמונה כללית חיובית. אפשר להעמיק ולבנות thesis קנייה מסודר.")
elif score == 2:
    st.warning("תמונה מעורבת. לא למהר — להשלים בדיקה בדפי Fundamentals + Peers.")
else:
    st.error("כרגע לא מספיק חזק. עדיף להמתין או לבדוק טיקר אחר ללמידה.")

st.markdown("**הצעד הבא שלך (בדיוק):**")
st.markdown("1. עבור ל־`02_Fundamentals_Valuation` ובדוק Altman Z + Margin of Safety.")
st.markdown("2. עבור ל־`05_Peer_Comparison` וראה אם החברה יקרה מהענף.")
st.markdown("3. חזור ל־`04_Portfolio_Quiz` וקבל החלטת סימולציה קטנה (לא מלאה).")

if data.get("errors"):
    section_divider()
    st.info("חלק מהמדדים לא נטענו כרגע. זה לא חוסם שימוש במסך.")
    for err in data["errors"]:
        st.caption(f"- {err}")
