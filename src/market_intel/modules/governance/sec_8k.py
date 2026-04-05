from __future__ import annotations

from market_intel.domain.entities.filing import FilingRecord


def filter_material_8k(filings: list[FilingRecord]) -> list[FilingRecord]:
    """Return 8-K filings (caller typically pre-filters by form)."""
    return [f for f in filings if f.form == "8-K"]
