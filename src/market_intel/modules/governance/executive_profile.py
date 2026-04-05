from __future__ import annotations

from market_intel.domain.entities.executive import ExecutiveProfile


def merge_executive_rows(rows: list[ExecutiveProfile]) -> list[ExecutiveProfile]:
    """Deduplicate executives by (symbol, name) keeping the richest record."""
    key_map: dict[tuple[str, str], ExecutiveProfile] = {}
    for r in rows:
        k = (r.symbol, r.name.strip().lower())
        cur = key_map.get(k)
        if cur is None:
            key_map[k] = r
            continue
        if (r.total_comp_usd or 0) >= (cur.total_comp_usd or 0):
            key_map[k] = r
    return list(key_map.values())
