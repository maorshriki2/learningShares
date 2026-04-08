from __future__ import annotations

from typing import Any

import streamlit as st


def _badge(label: str) -> tuple[str, str]:
    l = (label or "").strip().lower()
    if l == "buy":
        return ("BUY", "green")
    if l == "sell":
        return ("SELL", "red")
    if l == "hold":
        return ("HOLD", "yellow")
    return ("WATCH", "blue")


def _direction_he(direction: str | None) -> str:
    d = (direction or "").strip().lower()
    if d == "up":
        return "כיוון חיובי (Up)"
    if d == "down_or_flat":
        return "שטוח/שלילי (Down/Flat)"
    if d == "mixed":
        return "מעורב (Mixed)"
    return "לא זמין"


def render_stock360_composed_panel(result: dict[str, Any], *, include_explain: bool = True) -> None:
    """
    Render the composed Stock360 payload coming from `analysis_artifact["stock360"]`.
    This is NOT the legacy `/stock360/{symbol}/final-verdict` schema.
    """
    if not isinstance(result, dict) or not result.get("ok", False):
        st.error(result.get("message") if isinstance(result, dict) else "Stock360 failed.")
        st.json(result)
        return

    label = str(result.get("final_label") or "watch")
    direction = str(result.get("direction") or "")
    conf = result.get("confidence")
    req_entry = result.get("required_entry_price")

    lab, _color = _badge(label)
    c1, c2, c3, c4 = st.columns([1.2, 1.6, 1.2, 1.6])
    c1.metric("Verdict", lab)
    c2.metric("כיוון משוער", _direction_he(direction))
    c3.metric("Confidence", f"{float(conf)*100:.0f}%" if isinstance(conf, (int, float)) else "—")
    c4.metric("מחיר כניסה (אם זמין)", f"${float(req_entry):,.2f}" if isinstance(req_entry, (int, float)) else "—")

    reasons = result.get("key_reasons_he") or []
    risks = result.get("risks_he") or []

    st.divider()
    st.markdown("### למה יצא כך (Key reasons)")
    if isinstance(reasons, list) and reasons:
        for r in reasons[:10]:
            st.markdown(f"- {r}")
    else:
        st.info("אין נימוקים זמינים.")

    st.markdown("### סיכונים/הסתייגויות")
    if isinstance(risks, list) and risks:
        for r in risks[:10]:
            st.markdown(f"- {r}")
    else:
        st.success("אין סיכונים חזקים שסומנו (לא אומר שאין סיכון).")

    if include_explain:
        with st.expander("Trace / Explain (raw)", expanded=False):
            st.json(
                {
                    "trace": result.get("trace"),
                    "explain": result.get("explain"),
                }
            )

