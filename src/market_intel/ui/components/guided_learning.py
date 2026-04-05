from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class GuidedStep:
    id: str
    page_label: str
    page_path: str
    look_for: str
    why: str
    conclusion: str


_DEFAULT_STEPS: list[GuidedStep] = [
    GuidedStep(
        id="charting",
        page_label="01 — Charting Lab",
        page_path="pages/01_Charting_Lab.py",
        look_for="RSI, MACD crossover, and trend structure.",
        why="This gives a quick read of momentum and entry timing risk.",
        conclusion="If RSI is extreme and MACD confirms reversal, move to fundamentals before action.",
    ),
    GuidedStep(
        id="fundamentals",
        page_label="02 — Fundamentals",
        page_path="pages/02_Fundamentals_Valuation.py",
        look_for="P/E, ROIC, Altman Z, and DCF margin of safety.",
        why="This validates whether the business quality supports current price.",
        conclusion="If quality is strong and valuation discount exists, thesis becomes stronger.",
    ),
    GuidedStep(
        id="governance",
        page_label="03 — Governance",
        page_path="pages/03_Governance_Sentiment.py",
        look_for="Insider transactions, 8-K events, and FinBERT tone.",
        why="Management behavior and event risk can invalidate a good valuation story.",
        conclusion="If governance is clean and sentiment stable, conviction increases.",
    ),
    GuidedStep(
        id="peers",
        page_label="05 — Peer Comparison",
        page_path="pages/05_Peer_Comparison.py",
        look_for="Relative P/E, EV/EBITDA, and operating margin vs sector average.",
        why="Cheap absolute valuation can still be expensive relative to peers.",
        conclusion="Prefer setups with lower multiples and better margins than peers.",
    ),
    GuidedStep(
        id="macro",
        page_label="06 — Macro & WACC",
        page_path="pages/06_Macro_Simulation.py",
        look_for="Sensitivity of fair value when risk-free rate rises.",
        why="Rate shocks can compress valuation even for good companies.",
        conclusion="If fair value collapses under small rate changes, demand larger safety margin.",
    ),
    GuidedStep(
        id="portfolio",
        page_label="04 — Portfolio & Quiz",
        page_path="pages/04_Portfolio_Quiz.py",
        look_for="Alpha vs benchmark and concentration risk.",
        why="Learning is complete only when decisions outperform with controlled risk.",
        conclusion="Keep positions with proven thesis and reduce concentrated, weak-conviction bets.",
    ),
]


def render_guided_learning_sidebar(
    current_page: str,
    ticker: str | None = None,
    show_symbol_input: bool = True,
) -> str:
    symbol = (ticker or st.session_state.get("guided_symbol") or "AAPL").strip().upper()
    if not symbol:
        symbol = "AAPL"
    with st.sidebar:
        st.markdown("## Guided Learning Mode")
        if show_symbol_input:
            if "guided_symbol" not in st.session_state:
                st.session_state["guided_symbol"] = symbol
            symbol = st.text_input("Ticker for walkthrough", key="guided_symbol").strip().upper()
            if symbol:
                st.session_state["guided_symbol_last_nonempty"] = symbol
            else:
                symbol = str(st.session_state.get("guided_symbol_last_nonempty") or "AAPL").strip().upper()
                st.caption("Empty symbol is not allowed. Reusing last valid symbol.")
        else:
            st.session_state["guided_symbol"] = symbol
            st.markdown(f"**Ticker for walkthrough:** `{symbol}`")
        st.caption("Follow the checklist to connect chart, value, risk, and decision.")

        for idx, step in enumerate(_DEFAULT_STEPS, start=1):
            checked_key = f"guided_{symbol}_{step.id}_done"
            checked = st.checkbox(f"{idx}. {step.page_label}", key=checked_key)
            with st.expander(f"What to check: {step.page_label}", expanded=(step.id == current_page and not checked)):
                st.write(f"**Look for:** {step.look_for}")
                st.write(f"**Why it matters:** {step.why}")
                st.write(f"**Conclusion to draw:** {step.conclusion}")
                if hasattr(st, "page_link"):
                    st.page_link(step.page_path, label=f"Open {step.page_label}")
                else:
                    st.markdown(f"`{step.page_path}`")

        completed = sum(1 for s in _DEFAULT_STEPS if st.session_state.get(f"guided_{symbol}_{s.id}_done"))
        st.progress(completed / len(_DEFAULT_STEPS))
        st.caption(f"Progress: {completed}/{len(_DEFAULT_STEPS)} steps completed for {symbol}.")
    return symbol
