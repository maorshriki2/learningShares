from __future__ import annotations

from typing import Any


def extract_tag_history(
    company_facts: dict[str, Any],
    taxonomy: str,
    tag: str,
    unit: str = "USD",
) -> list[tuple[str, float]]:
    """
    Parse SEC companyfacts JSON for a single XBRL tag, returning (YYYY-MM-DD, value) sorted ascending.
    """
    facts = company_facts.get("facts", {})
    tax = facts.get(taxonomy, {})
    node = tax.get(tag)
    if not node:
        return []
    units = node.get("units", {})
    series = units.get(unit) or next(iter(units.values()), [])
    out: list[tuple[str, float]] = []
    for row in series:
        end = row.get("end")
        val = row.get("val")
        if end is None or val is None:
            continue
        fp = row.get("fp")
        if fp is not None and fp not in ("FY", "Q1", "Q2", "Q3", "Q4"):
            continue
        try:
            out.append((str(end), float(val)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda x: x[0])
    return out
