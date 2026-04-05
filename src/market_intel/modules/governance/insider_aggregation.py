from __future__ import annotations

from dataclasses import dataclass

from market_intel.domain.entities.insider_transaction import InsiderTransaction


@dataclass(frozen=True)
class InsiderSummary:
    buy_count: int
    sell_count: int
    buy_shares: float
    sell_shares: float
    net_shares: float


def aggregate_insider_transactions(rows: list[InsiderTransaction]) -> InsiderSummary:
    buy_keywords = ("buy", "purchase", "acquire", "grant", "award")
    sell_keywords = ("sale", "sell", "dispose", "disposition")
    buy_count = sell_count = 0
    buy_shares = sell_shares = 0.0
    for r in rows:
        t = r.transaction_type.lower()
        if any(k in t for k in buy_keywords):
            buy_count += 1
            buy_shares += max(r.shares, 0.0)
        elif any(k in t for k in sell_keywords):
            sell_count += 1
            sell_shares += max(r.shares, 0.0)
    return InsiderSummary(
        buy_count=buy_count,
        sell_count=sell_count,
        buy_shares=buy_shares,
        sell_shares=sell_shares,
        net_shares=buy_shares - sell_shares,
    )
