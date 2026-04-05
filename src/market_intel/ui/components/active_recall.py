from __future__ import annotations

import streamlit as st


def render_active_recall_checkpoint(
    page_key: str,
    prompt: str,
    choices: list[str],
    correct_index: int,
    explanation: str,
) -> None:
    st.markdown("### 🧠 Active Recall Checkpoint")
    selected = st.radio(
        prompt,
        options=list(range(len(choices))),
        format_func=lambda i: choices[i],
        key=f"{page_key}_recall_choice",
    )
    if st.button("בדוק תשובה", key=f"{page_key}_recall_submit"):
        if selected == correct_index:
            st.success("תשובה נכונה. מצוין.")
        else:
            st.error(f"תשובה לא נכונה. התשובה הנכונה: {choices[correct_index]}")
        st.info(explanation)
