from __future__ import annotations

import numpy as np
import pandas as pd


def portfolio_beta(
    weights: dict[str, float],
    asset_betas: dict[str, float],
) -> float:
    """
    Weighted average beta under the simplifying assumption of zero cross-asset correlation
    in idiosyncratic risk (educational approximation).
    """
    total_w = sum(max(w, 0.0) for w in weights.values())
    if total_w <= 0:
        return 1.0
    b = 0.0
    for sym, w in weights.items():
        bw = asset_betas.get(sym, 1.0)
        b += (max(w, 0.0) / total_w) * bw
    return float(b)


def beta_from_returns(
    asset_returns: pd.Series,
    market_returns: pd.Series,
) -> float:
    aligned = pd.concat([asset_returns, market_returns], axis=1).dropna()
    if len(aligned) < 10:
        return 1.0
    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
    var_m = np.var(aligned.iloc[:, 1])
    if var_m == 0:
        return 1.0
    return float(cov / var_m)
