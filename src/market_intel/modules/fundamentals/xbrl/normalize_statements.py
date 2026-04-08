from __future__ import annotations

from collections import defaultdict
from typing import Any

from market_intel.modules.fundamentals.xbrl.parse_facts import extract_tag_history

# Shared fallbacks for SEC companyfacts where the primary US-GAAP tag is missing or stale
# (e.g. banks / fintech: no `Revenues`, sparse `OperatingIncomeLoss`).
# Order: broader / standard concepts first; later tags only fill years still missing.
REVENUE_FALLBACK_TAGS: tuple[str, ...] = (
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
    "RevenuesNetOfInterestExpense",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "InsuranceServicesRevenue",
    "RegulatedOperatingRevenue",
)
OPERATING_INCOME_FALLBACK_TAGS: tuple[str, ...] = (
    "OperatingIncomeLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxExpenseBenefit",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxMinorityInterestAndIncomeLossFromEquityMethodInvestments",
)
COST_OF_REVENUE_FALLBACK_TAGS: tuple[str, ...] = (
    "CostOfRevenue",
    "CostOfGoodsSold",
    "CostOfGoodsAndServicesSold",
    "CostOfServices",
)
NET_INCOME_FALLBACK_TAGS: tuple[str, ...] = (
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAvailableToCommonStockholdersDiluted",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
)
EQUITY_FALLBACK_TAGS: tuple[str, ...] = (
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest",
    "PartnersCapital",
    "MembersCapital",
    "MembersEquity",
)
OCF_FALLBACK_TAGS: tuple[str, ...] = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
CAPEX_FALLBACK_TAGS: tuple[str, ...] = (
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsForCapitalImprovements",
)
DEPRECIATION_FALLBACK_TAGS: tuple[str, ...] = (
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "Depreciation",
)


def annual_series_preferred_tags_per_year(
    company_facts: dict[str, Any],
    taxonomy: str,
    tags: tuple[str, ...],
) -> dict[int, float]:
    """
    For each fiscal year, use the first tag in `tags` that reports that year; later tags
    only fill years still missing. Within a (tag, year), keep the row with the latest `end`
    date (typical FY filing).
    """
    per_year: dict[int, float] = {}
    for tag in tags:
        hist = extract_tag_history(company_facts, taxonomy, tag)
        by_year: dict[int, list[tuple[str, float]]] = defaultdict(list)
        for end, val in hist:
            y = int(str(end)[:4])
            by_year[y].append((str(end), float(val)))
        for y, pairs in by_year.items():
            if y in per_year:
                continue
            _, v = max(pairs, key=lambda x: x[0])
            per_year[y] = v
    return per_year


def annual_series_first_matching_tag(
    company_facts: dict[str, Any],
    taxonomy: str,
    tags: tuple[str, ...],
) -> dict[int, float]:
    """
    First US-GAAP tag in `tags` that returns any facts wins; per calendar year keep
    the observation with the latest `end` date (FY filing).
    """
    for tag in tags:
        hist = extract_tag_history(company_facts, taxonomy, tag)
        if not hist:
            continue
        by_year: dict[int, list[tuple[str, float]]] = defaultdict(list)
        for end, val in hist:
            y = int(str(end)[:4])
            by_year[y].append((str(end), float(val)))
        out: dict[int, float] = {}
        for y, pairs in by_year.items():
            _, v = max(pairs, key=lambda x: x[0])
            out[y] = v
        return out
    return {}


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
