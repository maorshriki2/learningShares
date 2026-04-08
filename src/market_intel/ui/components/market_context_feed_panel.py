"""
UI shell for market narrative feed (news, speeches, rumors, corporate events).
Backend returns typed sections; items may be empty until providers are wired.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from market_intel.ui.components.cards import section_divider


def render_market_context_feed(payload: dict[str, Any]) -> None:
    """Render `/api/v1/market/{symbol}/context-feed` JSON."""
    if not payload.get("ok", False):
        st.error(payload.get("message_he") or payload.get("message") or "טעינת ההקשר נכשלה.")
        return

    msg = str(payload.get("message_he") or "").strip()
    if msg:
        st.info(msg)

    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        st.warning("אין עדיין סעיפים ממולאים — השכבה מוכנה לחיבור מקורות.")
        return

    for idx, raw in enumerate(sections):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title_he") or raw.get("title") or "סעיף").strip()
        sub = str(raw.get("subtitle_he") or "").strip()
        st.markdown(f"### {title}")
        if sub:
            st.caption(sub)

        items = raw.get("items")
        # Social section: AI synthesis on top + raw posts in an expander.
        if str(raw.get("id") or "").strip() == "rumors":
            bottom = str(raw.get("ai_bottom_line_he") or "").strip()
            verdict = str(raw.get("ai_verdict") or "").strip().lower()
            dbg = raw.get("ai_debug") if isinstance(raw.get("ai_debug"), dict) else None
            if isinstance(dbg, dict) and (dbg.get("total") is not None) and (dbg.get("included") is not None):
                try:
                    st.caption(
                        f"Used {int(dbg.get('included') or 0)}/{int(dbg.get('total') or 0)} posts "
                        f"(obvious={int(dbg.get('obvious') or 0)}, borderline={int(dbg.get('borderline') or 0)})"
                    )
                except Exception:
                    pass
            if bottom:
                header = "סיכום סנטימנט חברתי"
                body = f"**{header}:**\n\n{bottom}"
                if verdict == "bullish":
                    st.success(body)
                elif verdict == "bearish":
                    st.warning(body)
                else:
                    st.info(body)
            else:
                st.info("סיכום סנטימנט חברתי: לא זמין (דורש `ANTHROPIC_API_KEY` או שאין מספיק פוסטים רלוונטיים).")

            with st.expander("Raw posts (X + Truth Social)", expanded=False):
                if not isinstance(items, list) or not items:
                    st.markdown("*אין פריטים עדיין בקטגוריה הזו.*")
                else:
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        head = str(it.get("title") or "").strip() or "פריט"
                        summ = str(it.get("summary_he") or it.get("summary") or "").strip()
                        when = str(it.get("occurred_at") or "").strip()
                        st.markdown(f"**{head}**")
                        if when:
                            st.caption(when)
                        if summ:
                            st.markdown(summ)
                        url = str(it.get("url") or "").strip()
                        if url:
                            st.markdown(f"[מקור]({url})")
        else:
            if not isinstance(items, list) or not items:
                st.markdown("*אין פריטים עדיין בקטגוריה הזו.*")
            else:
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    head = str(it.get("title") or "").strip() or "פריט"
                    summ = str(it.get("summary_he") or it.get("summary") or "").strip()
                    when = str(it.get("occurred_at") or "").strip()
                    st.markdown(f"**{head}**")
                    if when:
                        st.caption(when)
                    if summ:
                        st.markdown(summ)
                    url = str(it.get("url") or "").strip()
                    if url:
                        st.markdown(f"[מקור]({url})")
        if idx < len(sections) - 1:
            section_divider()
