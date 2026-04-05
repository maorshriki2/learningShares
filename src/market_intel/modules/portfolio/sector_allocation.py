from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from market_intel.domain.entities.portfolio import Portfolio
from market_intel.domain.value_objects.sector import Sector


def sector_weights(
    portfolio: Portfolio,
    prices: dict[str, float],
    sector_map: dict[str, Sector],
) -> dict[str, float]:
    total = float(portfolio.cash_usd)
    sector_mv: dict[str, float] = defaultdict(float)
    for sym, pos in portfolio.positions.items():
        px = prices.get(sym)
        if px is None:
            continue
        mv = pos.quantity * px
        total += mv
        sec = sector_map.get(sym, Sector.UNKNOWN)
        sector_mv[sec.value] += mv
    if total <= 0:
        return {}
    return {k: v / total for k, v in sector_mv.items()}
