from __future__ import annotations

import streamlit as st

from market_intel.ui.formatters.bidi_text import ltr_embed as L


def dcf_controls() -> tuple[float, float, float]:
    st.markdown(f"#### הנחות {L('DCF')} (סליידרים ב־{L('Streamlit')})")
    growth = st.slider(
        f"צמיחה בשלב המפורש (שנים 1–5) — הכנסות / {L('FCF')}",
        0.0,
        0.25,
        0.05,
        0.005,
        help=(
            "בפרודקט: צמיחה קבועה אילוסטרטיבית לתקופה המפורשת של המודל. "
            "הזזה למעלה = תרחיש שווקי/תפעולי אופטימי יותר (לא בהכרח ריאלי)."
        ),
    )
    terminal = st.slider(
        f"צמיחה טרמינלית ({L('perpetuity')})",
        0.0,
        0.06,
        0.02,
        0.001,
        help=(
            f"בשלב גורדון: צמיחה לנצח של התזרים. חייבת להיות נמוכה מ־{L('WACC')} "
            "אחרת המודל מתפרק מתמטית; בפרקטיקה מגבילים לרמה מאופקת."
        ),
    )
    wacc = st.slider(
        f"{L('WACC')} (שיעור היוון / הניכוי)",
        0.04,
        0.20,
        0.09,
        0.001,
        help=(
            f"קצב הניכוי לתזרימים צפויים. {L('WACC')} גבוה יותר → ערך נוכחי נמוך יותר "
            "(בהנחות אחרות זהות)."
        ),
    )
    return growth, terminal, wacc
