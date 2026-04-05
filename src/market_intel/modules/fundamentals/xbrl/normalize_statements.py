from __future__ import annotations

from collections import defaultdict
from typing import Any

from market_intel.modules.fundamentals.xbrl.parse_facts import extract_tag_history


def annual_series_from_facts(
    company_facts: dict[str, Any],
    tag_map: dict[str, tuple[str, str]],
) -> dict[str, dict[int, float]]:
    """
    Collapse SEC facts to fiscal-year values per tag.
    tag_map: output_key -> (taxonomy, tag_name), e.g. us-gaap Revenues
    For duplicate end-dates, keep the last filing occurrence (SEC data is ordered).
    """
    result: dict[str, dict[int, float]] = defaultdict(dict)
    for key, (tax, tag) in tag_map.items():
        hist = extract_tag_history(company_facts, tax, tag)
        for end, val in hist:
            year = int(end[:4])
            result[key][year] = val
    return dict(result)
