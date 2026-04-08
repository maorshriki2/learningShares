from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from market_intel.ui.formatters.bidi_text import ltr_embed as L
from market_intel.ui.formatters.usd_compact import format_pivot_currency_cells


def statements_tabs(payload: dict[str, Any]) -> None:
    inc = payload.get("income") or []
    bal = payload.get("balance") or []
    cf = payload.get("cashflow") or []

    def pivot(rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        return df.pivot_table(index="label", columns="fiscal_year", values="value", aggfunc="last")

    t1, t2, t3 = st.tabs(["Income", "Balance Sheet", "Cash Flow"])
    st.caption(
        f"ערכים בדולרים מקוצרים ({L('$K')} / {L('$M')} / {L('$B')}) — "
        f"מקור: {L('SEC')} {L('XBRL')} company facts."
    )
    with t1:
        st.dataframe(format_pivot_currency_cells(pivot(inc)), width="stretch")
    with t2:
        st.dataframe(format_pivot_currency_cells(pivot(bal)), width="stretch")
    with t3:
        st.dataframe(format_pivot_currency_cells(pivot(cf)), width="stretch")
