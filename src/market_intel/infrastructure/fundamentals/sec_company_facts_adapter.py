from __future__ import annotations

import json
from typing import Any

import httpx

from market_intel.config.settings import Settings
from market_intel.domain.entities.financial_statement import StatementLine, StatementType
from market_intel.domain.ports.fundamentals_port import FundamentalsPort
from market_intel.infrastructure.cache.redis_cache import MemoryCache, RedisCache, cache_key
from market_intel.infrastructure.http.rate_limit import AsyncRateLimiter
from market_intel.infrastructure.sec.sec_edgar_adapter import SecEdgarHttpAdapter
from market_intel.modules.fundamentals.statements.balance import balance_sheet_lines
from market_intel.modules.fundamentals.statements.cashflow import cashflow_lines
from market_intel.modules.fundamentals.statements.income import income_statement_lines
from market_intel.modules.fundamentals.xbrl.normalize_statements import (
    CAPEX_FALLBACK_TAGS,
    COST_OF_REVENUE_FALLBACK_TAGS,
    DEPRECIATION_FALLBACK_TAGS,
    EQUITY_FALLBACK_TAGS,
    NET_INCOME_FALLBACK_TAGS,
    OCF_FALLBACK_TAGS,
    OPERATING_INCOME_FALLBACK_TAGS,
    REVENUE_FALLBACK_TAGS,
    annual_series_from_facts,
    annual_series_preferred_tags_per_year,
)

_TAG_MAP: dict[str, tuple[str, str]] = {
    "revenue": ("us-gaap", "Revenues"),
    "net_income": ("us-gaap", "NetIncomeLoss"),
    "gross_profit": ("us-gaap", "GrossProfit"),
    "operating_income": ("us-gaap", "OperatingIncomeLoss"),
    "assets": ("us-gaap", "Assets"),
    "liabilities": ("us-gaap", "Liabilities"),
    "equity": ("us-gaap", "StockholdersEquity"),
    "current_assets": ("us-gaap", "AssetsCurrent"),
    "current_liabilities": ("us-gaap", "LiabilitiesCurrent"),
    "operating_cf": ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
    "capex": ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
}


class SecCompanyFactsFundamentalsAdapter(FundamentalsPort):
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
        rate_limiter: AsyncRateLimiter,
        sec: SecEdgarHttpAdapter,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache
        self._limiter = rate_limiter
        self._sec = sec

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}

    async def get_company_facts(self, symbol: str) -> dict[str, Any]:
        return await self._company_facts(symbol)

    async def _company_facts(self, symbol: str) -> dict[str, Any]:
        cik = await self._sec.resolve_cik(symbol)
        ck = cache_key("sec:companyfacts", {"cik": cik})
        cached = await self._cache.get(ck)
        if cached:
            return json.loads(cached)
        await self._limiter.acquire()
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
        r = await self._client.get(url, headers=self._headers())
        r.raise_for_status()
        data = r.json()
        await self._cache.set(ck, json.dumps(data), ttl_seconds=86400)
        return data

    async def get_statement_series(
        self,
        symbol: str,
        statement_type: StatementType,
        years: int,
    ) -> list[StatementLine]:
        facts = await self._company_facts(symbol)
        series = annual_series_from_facts(facts, _TAG_MAP)
        ni = series.get("net_income", {})
        assets = series.get("assets", {})
        liab = series.get("liabilities", {})
        eq = series.get("equity", {})
        ca = series.get("current_assets", {})
        cl = series.get("current_liabilities", {})
        ocf = series.get("operating_cf", {})
        capex = series.get("capex", {})

        rev = series.get("revenue", {})
        gp: dict[int, float] = dict(series.get("gross_profit", {}))
        oi = series.get("operating_income", {})

        if statement_type == StatementType.INCOME:
            rev_fb = annual_series_preferred_tags_per_year(
                facts, "us-gaap", REVENUE_FALLBACK_TAGS
            )
            if rev_fb:
                rev = rev_fb
            gp_tag = annual_series_preferred_tags_per_year(facts, "us-gaap", ("GrossProfit",))
            gp = dict(gp_tag) if gp_tag else dict(gp)
            cost_ser = annual_series_preferred_tags_per_year(
                facts, "us-gaap", COST_OF_REVENUE_FALLBACK_TAGS
            )
            for y in set(rev.keys()) | set(cost_ser.keys()):
                if y in gp:
                    continue
                if y in rev and y in cost_ser:
                    gp[y] = rev[y] - cost_ser[y]
            oi_fb = annual_series_preferred_tags_per_year(
                facts, "us-gaap", OPERATING_INCOME_FALLBACK_TAGS
            )
            if oi_fb:
                oi = oi_fb
            ni_fb = annual_series_preferred_tags_per_year(
                facts, "us-gaap", NET_INCOME_FALLBACK_TAGS
            )
            if ni_fb:
                ni = ni_fb

        if statement_type == StatementType.BALANCE:
            eq_fb = annual_series_preferred_tags_per_year(
                facts, "us-gaap", EQUITY_FALLBACK_TAGS
            )
            if eq_fb:
                eq = eq_fb

        if statement_type == StatementType.CASHFLOW:
            ocf_fb = annual_series_preferred_tags_per_year(
                facts, "us-gaap", OCF_FALLBACK_TAGS
            )
            if ocf_fb:
                ocf = ocf_fb
            capex_fb = annual_series_preferred_tags_per_year(
                facts, "us-gaap", CAPEX_FALLBACK_TAGS
            )
            if capex_fb:
                capex = capex_fb

        year_union: set[int] = set()
        for d in series.values():
            if d:
                year_union |= set(d.keys())
        if statement_type == StatementType.INCOME:
            year_union |= set(rev.keys()) | set(gp.keys()) | set(oi.keys()) | set(ni.keys())
        elif statement_type == StatementType.BALANCE:
            year_union |= (
                set(assets.keys())
                | set(liab.keys())
                | set(eq.keys())
                | set(ca.keys())
                | set(cl.keys())
            )
        elif statement_type == StatementType.CASHFLOW:
            year_union |= set(ocf.keys()) | set(capex.keys())

        all_years = sorted(year_union, reverse=True)[:years]
        years_list = sorted(all_years)

        fcf: dict[int, float] = {}
        for y in years_list:
            if y in ocf and y in capex:
                fcf[y] = ocf[y] - abs(capex[y])

        if statement_type == StatementType.INCOME:
            ebitda_direct = annual_series_preferred_tags_per_year(
                facts,
                "us-gaap",
                (
                    "EarningsBeforeInterestTaxesDepreciationAmortization",
                    "EarningsBeforeInterestTaxesDepreciationAndAmortization",
                ),
            )
            dep_fallback = annual_series_preferred_tags_per_year(
                facts, "us-gaap", DEPRECIATION_FALLBACK_TAGS
            )
            ebitda_merged: dict[int, float] = dict(ebitda_direct)
            for y in years_list:
                if y in ebitda_merged:
                    continue
                oyv = oi.get(y) if oi else None
                dv = dep_fallback.get(y)
                if oyv is not None and dv is not None:
                    ebitda_merged[y] = float(oyv) + float(dv)
            ebitda_arg = ebitda_merged if ebitda_merged else None
            return income_statement_lines(
                symbol,
                years_list,
                revenues=rev,
                net_income=ni,
                gross_profit=gp or None,
                operating_income=oi or None,
                ebitda=ebitda_arg,
            )
        if statement_type == StatementType.BALANCE:
            return balance_sheet_lines(
                symbol,
                years_list,
                total_assets=assets,
                total_liabilities=liab,
                equity=eq or None,
                current_assets=ca or None,
                current_liabilities=cl or None,
            )
        return cashflow_lines(
            symbol,
            years_list,
            operating_cashflow=ocf,
            capex=capex or None,
            free_cash_flow=fcf or None,
        )
