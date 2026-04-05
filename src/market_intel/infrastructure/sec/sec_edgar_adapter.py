from __future__ import annotations

import json
from datetime import date
from typing import Any

import httpx

from market_intel.config.settings import Settings
from market_intel.domain.entities.filing import FilingRecord
from market_intel.domain.entities.insider_transaction import InsiderTransaction
from market_intel.domain.ports.sec_edgar_port import SecEdgarPort
from market_intel.infrastructure.cache.redis_cache import MemoryCache, RedisCache, cache_key
from market_intel.infrastructure.http.rate_limit import AsyncRateLimiter
from market_intel.infrastructure.sec.edgar_documents import filing_document_url
from market_intel.infrastructure.sec.edgar_submissions import filter_recent_filings
from market_intel.modules.governance.sec_form4 import parse_form4_xml_to_transactions


class SecEdgarHttpAdapter(SecEdgarPort):
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        cache: MemoryCache | RedisCache,
        rate_limiter: AsyncRateLimiter,
    ) -> None:
        self._settings = settings
        self._client = client
        self._cache = cache
        self._limiter = rate_limiter
        self._ticker_map: dict[str, str] | None = None

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}

    @staticmethod
    def _safe_json_loads(payload: str | bytes | None) -> Any | None:
        if payload is None:
            return None
        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="ignore")
            text = str(payload).strip()
            if not text:
                return None
            return json.loads(text)
        except Exception:
            return None

    async def _load_ticker_map(self) -> dict[str, str]:
        if self._ticker_map is not None:
            return self._ticker_map
        ck = "sec:company_tickers"
        cached = await self._cache.get(ck)
        if cached:
            parsed = self._safe_json_loads(cached)
            if isinstance(parsed, dict):
                self._ticker_map = parsed
                return self._ticker_map
        await self._limiter.acquire()
        r = await self._client.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=self._headers(),
        )
        r.raise_for_status()
        data = r.json()
        mp: dict[str, str] = {}
        for row in data.values():
            t = str(row["ticker"]).upper()
            cik = str(row["cik_str"]).zfill(10)
            mp[t] = cik
        self._ticker_map = mp
        await self._cache.set(ck, json.dumps(mp), ttl_seconds=86400)
        return mp

    async def resolve_cik(self, symbol: str) -> str:
        mp = await self._load_ticker_map()
        cik = mp.get(symbol.upper())
        if not cik:
            raise ValueError(f"Unknown ticker for SEC: {symbol}")
        return cik

    async def _submissions(self, cik: str) -> dict[str, Any]:
        ck = cache_key("sec:submissions", {"cik": cik})
        cached = await self._cache.get(ck)
        if cached:
            parsed = self._safe_json_loads(cached)
            if isinstance(parsed, dict):
                return parsed
        await self._limiter.acquire()
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        r = await self._client.get(url, headers=self._headers())
        r.raise_for_status()
        data = r.json()
        await self._cache.set(ck, json.dumps(data), ttl_seconds=3600)
        return data

    async def recent_filings(self, symbol: str, forms: list[str], limit: int) -> list[FilingRecord]:
        cik = await self.resolve_cik(symbol)
        sub = await self._submissions(cik)
        wanted = set(forms)
        rows = filter_recent_filings(sub, wanted, limit)
        out: list[FilingRecord] = []
        cik_num = str(int(cik))
        for row in rows:
            fd = date.fromisoformat(row["filingDate"])
            acc = row["accessionNumber"]
            doc = row.get("primaryDocument") or ""
            url = None
            if doc:
                url = filing_document_url(cik_num, acc, doc)
            out.append(
                FilingRecord(
                    cik=cik,
                    accession=acc,
                    form=row["form"],
                    filed=fd,
                    primary_document=doc or None,
                    filing_url=url,
                    description=None,
                )
            )
        return out

    async def insider_form4_recent(self, symbol: str, limit: int) -> list[InsiderTransaction]:
        filings = await self.recent_filings(symbol, ["4"], limit=limit)
        all_tx: list[InsiderTransaction] = []
        for f in filings:
            if not f.primary_document or not f.filing_url:
                continue
            ck = cache_key("sec:form4", {"url": str(f.filing_url)})
            cached = await self._cache.get(ck)
            if cached:
                parsed = self._safe_json_loads(cached)
                if isinstance(parsed, list):
                    for item in parsed:
                        all_tx.append(InsiderTransaction.model_validate(item))
                    continue
            await self._limiter.acquire()
            r = await self._client.get(str(f.filing_url), headers=self._headers())
            if r.status_code != 200:
                continue
            text = r.text
            txs = parse_form4_xml_to_transactions(symbol, text, default_filing_date=f.filed)
            serializable = [t.model_dump(mode="json") for t in txs]
            await self._cache.set(ck, json.dumps(serializable), ttl_seconds=86400)
            all_tx.extend(txs)
        return all_tx[:limit]
