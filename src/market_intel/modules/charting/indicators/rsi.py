from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    c = close.astype(float)
    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().to_numpy(dtype=float)
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().to_numpy(dtype=float)
    r = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss > 0)
    base = 100.0 - (100.0 / (1.0 + r))
    out = np.where(avg_loss > 0, base, np.where(avg_gain > 0, 100.0, 50.0))
    return pd.Series(np.asarray(out, dtype=float), index=close.index)
