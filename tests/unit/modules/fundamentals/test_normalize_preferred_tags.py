from market_intel.modules.fundamentals.xbrl.normalize_statements import (
    REVENUE_FALLBACK_TAGS,
    annual_series_preferred_tags_per_year,
)


def _usd_fact(tag: str, rows: list[dict]) -> dict:
    return {"facts": {"us-gaap": {tag: {"units": {"USD": rows}}}}}


def test_preferred_tags_per_year_later_tag_fills_missing_years() -> None:
    """When the first tag stops filing (e.g. sparse OperatingIncomeLoss), use fallbacks."""
    facts = _usd_fact(
        "OperatingIncomeLoss",
        [{"end": "2020-12-31", "val": -600_000, "fp": "FY"}],
    )
    facts["facts"]["us-gaap"][
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
    ] = {
        "units": {
            "USD": [
                {"end": "2020-12-31", "val": 9e8, "fp": "FY"},
                {"end": "2024-12-31", "val": 233e6, "fp": "FY"},
            ]
        }
    }
    out = annual_series_preferred_tags_per_year(
        facts,
        "us-gaap",
        (
            "OperatingIncomeLoss",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ),
    )
    assert out[2020] == -600_000.0
    assert out[2024] == 233e6


def test_preferred_tags_revenue_bank_style() -> None:
    facts = _usd_fact(
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        [{"end": "2024-12-31", "val": 500e6, "fp": "FY"}],
    )
    facts["facts"]["us-gaap"]["RevenuesNetOfInterestExpense"] = {
        "units": {
            "USD": [
                {"end": "2024-12-31", "val": 2.6e9, "fp": "FY"},
            ]
        }
    }
    out = annual_series_preferred_tags_per_year(facts, "us-gaap", REVENUE_FALLBACK_TAGS)
    assert out[2024] == 2.6e9
