from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


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
    with t1:
        st.dataframe(pivot(inc), width="stretch")
    with t2:
        st.dataframe(pivot(bal), width="stretch")
    with t3:
        st.dataframe(pivot(cf), width="stretch")
