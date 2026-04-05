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
from market_intel.modules.fundamentals.xbrl.normalize_statements import annual_series_from_facts


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
        all_years = sorted(
            set().union(*[set(d.keys()) for d in series.values() if d]),
            reverse=True,
        )[:years]
        years_list = sorted(all_years)
        rev = series.get("revenue", {})
        ni = series.get("net_income", {})
        gp = series.get("gross_profit", {})
        oi = series.get("operating_income", {})
        assets = series.get("assets", {})
        liab = series.get("liabilities", {})
        eq = series.get("equity", {})
        ca = series.get("current_assets", {})
        cl = series.get("current_liabilities", {})
        ocf = series.get("operating_cf", {})
        capex = series.get("capex", {})
        fcf: dict[int, float] = {}
        for y in years_list:
            if y in ocf and y in capex:
                fcf[y] = ocf[y] - abs(capex[y])

        if statement_type == StatementType.INCOME:
            return income_statement_lines(
                symbol,
                years_list,
                revenues=rev,
                net_income=ni,
                gross_profit=gp or None,
                operating_income=oi or None,
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
