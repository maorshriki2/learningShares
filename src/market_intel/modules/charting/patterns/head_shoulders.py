from __future__ import annotations

import numpy as np
import pandas as pd

from market_intel.modules.charting.patterns.pattern_types import PatternAnnotation


def _local_extrema_indices(series: np.ndarray, order: int = 2) -> tuple[list[int], list[int]]:
    """Simple scipy-free peak/trough detection using rolling max/min."""
    n = len(series)
    peaks: list[int] = []
    troughs: list[int] = []
    for i in range(order, n - order):
        window = series[i - order : i + order + 1]
        if series[i] == np.max(window) and np.sum(window == series[i]) == 1:
            peaks.append(i)
        if series[i] == np.min(window) and np.sum(window == series[i]) == 1:
            troughs.append(i)
    return peaks, troughs


def detect_head_and_shoulders(
    df: pd.DataFrame,
    order: int = 3,
    symmetry_tolerance: float = 0.04,
    neckline_break_frac: float = 0.002,
) -> list[PatternAnnotation]:
    """
    Heuristic Head & Shoulders (bearish reversal) on closing prices.
    Looks for three peaks with middle highest and two shoulders similar height,
    with two intervening troughs forming a neckline; last bars break neckline down.
    """
    if df.empty or len(df) < order * 6:
        return []
    close = df["close"].astype(float).values
    idx = df.index
    peaks, troughs = _local_extrema_indices(close, order=order)
    annotations: list[PatternAnnotation] = []
    for pi in range(1, len(peaks) - 1):
        ls_i, h_i, rs_i = peaks[pi - 1], peaks[pi], peaks[pi + 1]
        left_sh = float(close[ls_i])
        head = float(close[h_i])
        right_sh = float(close[rs_i])
        if not (head > left_sh and head > right_sh):
            continue
        shoulder_avg = (left_sh + right_sh) / 2.0
        if shoulder_avg <= 0:
            continue
        asym = abs(left_sh - right_sh) / shoulder_avg
        if asym > symmetry_tolerance * 5:
            continue
        troughs_between = [t for t in troughs if ls_i < t < h_i]
        troughs_between2 = [t for t in troughs if h_i < t < rs_i]
        if not troughs_between or not troughs_between2:
            continue
        nl_left = troughs_between[-1]
        nl_right = troughs_between2[0]
        neckline = (float(close[nl_left]) + float(close[nl_right])) / 2.0
        last = float(close[-1])
        if last > neckline * (1.0 - neckline_break_frac):
            continue
        conf = max(0.0, min(1.0, 1.0 - asym / (symmetry_tolerance * 5)))
        start_t = idx[ls_i].to_pydatetime() if hasattr(idx[ls_i], "to_pydatetime") else None
        end_t = idx[-1].to_pydatetime() if hasattr(idx[-1], "to_pydatetime") else None
        annotations.append(
            PatternAnnotation(
                name="head_and_shoulders",
                start_index=int(ls_i),
                end_index=int(len(close) - 1),
                confidence=float(conf),
                meta={
                    "left_shoulder_index": ls_i,
                    "head_index": h_i,
                    "right_shoulder_index": rs_i,
                    "neckline": neckline,
                    "shoulder_symmetry_ratio": float(asym),
                },
                start_time=start_t,
                end_time=end_t,
            )
        )
        break
    return annotations
