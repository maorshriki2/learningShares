from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FibonacciRetracement:
    swing_high: float
    swing_low: float
    direction: str
    levels: dict[str, float]


def fibonacci_levels_from_swing(
    swing_high: float,
    swing_low: float,
    ratios: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786),
) -> FibonacciRetracement:
    """
    Compute retracement prices between a swing high and swing low.
    If uptrend (low -> high), retracements pull back from high toward low.
    """
    hi = max(swing_high, swing_low)
    lo = min(swing_high, swing_low)
    diff = hi - lo
    if diff <= 0:
        return FibonacciRetracement(
            swing_high=hi,
            swing_low=lo,
            direction="flat",
            levels={f"{int(r * 1000) / 10}%": hi for r in ratios},
        )
    direction = "up" if swing_low < swing_high else "down"
    levels: dict[str, float] = {}
    for r in ratios:
        key = f"{r:.3f}".rstrip("0").rstrip(".")
        if direction == "up":
            levels[key] = hi - diff * r
        else:
            levels[key] = lo + diff * r
    return FibonacciRetracement(swing_high=hi, swing_low=lo, direction=direction, levels=levels)
