from __future__ import annotations

import numpy as np
import pandas as pd

from market_intel.modules.charting.patterns.pattern_types import PatternAnnotation


def detect_bull_flag(
    df: pd.DataFrame,
    pole_lookback: int = 12,
    flag_lookback: int = 10,
    min_pole_return: float = 0.03,
    max_flag_depth: float = 0.02,
) -> list[PatternAnnotation]:
    """
    Heuristic bull flag: strong upward pole (impulse) followed by shallow
    downward or sideways drift (flag) with declining volume tendency.
    """
    if df.empty or len(df) < pole_lookback + flag_lookback + 2:
        return []
    close = df["close"].astype(float).values
    vol = df["volume"].astype(float).values
    idx = df.index
    annotations: list[PatternAnnotation] = []
    end = len(close) - 1
    flag_start = end - flag_lookback + 1
    pole_start = flag_start - pole_lookback
    if pole_start < 0:
        return []
    pole_ret = (close[flag_start - 1] - close[pole_start]) / max(close[pole_start], 1e-9)
    if pole_ret < min_pole_return:
        return []
    flag_seg = close[flag_start : end + 1]
    flag_high = float(np.max(flag_seg))
    flag_low = float(np.min(flag_seg))
    anchor = float(close[flag_start - 1])
    depth = (anchor - flag_low) / max(anchor, 1e-9)
    if depth > max_flag_depth * 3:
        return []
    vol_pole = float(np.mean(vol[pole_start:flag_start]))
    vol_flag = float(np.mean(vol[flag_start : end + 1]))
    if vol_pole > 0 and vol_flag > vol_pole * 1.15:
        return []
    breakout = close[end] > flag_high * 0.999
    conf = min(1.0, pole_ret / (min_pole_return * 2)) * (0.6 + 0.4 * float(breakout))
    start_t = idx[pole_start].to_pydatetime() if hasattr(idx[pole_start], "to_pydatetime") else None
    end_t = idx[end].to_pydatetime() if hasattr(idx[end], "to_pydatetime") else None
    annotations.append(
        PatternAnnotation(
            name="bull_flag",
            start_index=int(pole_start),
            end_index=int(end),
            confidence=float(conf),
            meta={
                "pole_return": float(pole_ret),
                "flag_depth_ratio": float(depth),
                "volume_ratio_flag_to_pole": float(vol_flag / vol_pole) if vol_pole > 0 else None,
                "breakout_confirmed": breakout,
            },
            start_time=start_t,
            end_time=end_t,
        )
    )
    return annotations
