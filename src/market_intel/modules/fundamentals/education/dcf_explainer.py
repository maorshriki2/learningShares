from __future__ import annotations

from market_intel.modules.fundamentals.valuation.dcf import DcfResult


def summarize_dcf(result: DcfResult, market_price: float | None) -> str:
    parts = [
        f"Enterprise value (DCF): {result.enterprise_value:,.0f}",
        f"PV explicit stage: {result.pv_explicit:,.0f}",
        f"PV terminal value: {result.pv_terminal:,.0f}",
    ]
    if result.implied_per_share is not None:
        parts.append(f"Implied equity value per share: {result.implied_per_share:.2f}")
    if market_price is not None and result.implied_per_share is not None:
        mos = (result.implied_per_share - market_price) / market_price * 100.0
        parts.append(f"Versus market {market_price:.2f}: {mos:+.1f}% margin of safety (raw)")
    return " | ".join(parts)


def margin_of_safety_note() -> str:
    return (
        "Margin of safety is the discount between your estimated intrinsic value and the price you pay. "
        "It buffers modeling error, competitive threats, and macro shocks. In DCF work, small changes "
        "to terminal growth or WACC dominate far-future value; treat the margin of safety as "
        "governance on overconfidence, not a precise statistical forecast."
    )
