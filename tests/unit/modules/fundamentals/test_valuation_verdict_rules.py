from __future__ import annotations

import math


def _label_for_price(
    *,
    price: float | None,
    intrinsic: float | None,
    mos_required: float = 0.15,
    premium_threshold: float = 0.15,
    terminal_weight_warn: bool = False,
    roic_lt_wacc: bool = False,
) -> str:
    """
    Mirror the transparent rule intent used in /valuation/{symbol}/verdict.
    This is a unit-level contract test for the rule mapping (not the API wiring).
    """
    label = "hold"
    if price is None or intrinsic is None or not math.isfinite(price) or not math.isfinite(intrinsic):
        label = "hold"
    else:
        entry = intrinsic * (1.0 - mos_required)
        if price <= entry:
            label = "buy"
        elif price >= intrinsic * (1.0 + premium_threshold):
            label = "sell"
        else:
            label = "hold"

    # downgrades
    if terminal_weight_warn and label == "buy":
        label = "hold"
    if roic_lt_wacc and label == "buy":
        label = "hold"
    return label


def test_buy_when_price_below_required_entry() -> None:
    assert _label_for_price(price=85, intrinsic=100, mos_required=0.15) == "buy"


def test_sell_when_price_above_premium_threshold() -> None:
    assert _label_for_price(price=120, intrinsic=100, premium_threshold=0.15) == "sell"


def test_hold_when_between_entry_and_premium() -> None:
    assert _label_for_price(price=95, intrinsic=100, mos_required=0.15, premium_threshold=0.15) == "hold"


def test_downgrade_buy_when_terminal_weight_warn() -> None:
    assert _label_for_price(price=80, intrinsic=100, terminal_weight_warn=True) == "hold"


def test_downgrade_buy_when_roic_lt_wacc() -> None:
    assert _label_for_price(price=80, intrinsic=100, roic_lt_wacc=True) == "hold"

