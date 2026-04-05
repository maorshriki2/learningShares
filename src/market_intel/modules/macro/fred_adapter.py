from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime
from typing import Any

import httpx


_FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
_FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

_KNOWN_RATES: dict[str, float] = {
    "DGS10": 4.35,
    "DGS2":  4.90,
    "DFF":   5.33,
}


class FredRatesAdapter:
    def __init__(self, fred_api_key: str | None = None) -> None:
        self._key = fred_api_key
        self._client = httpx.AsyncClient(timeout=12.0, follow_redirects=True)

    async def fetch_rate(self, series_id: str = "DGS10") -> float:
        try:
            rate = await asyncio.wait_for(self._fetch_csv(series_id), timeout=8.0)
            if rate is not None:
                return rate
        except Exception:
            pass
        if self._key:
            try:
                rate = await asyncio.wait_for(self._fetch_api(series_id), timeout=8.0)
                if rate is not None:
                    return rate
            except Exception:
                pass
        return _KNOWN_RATES.get(series_id, 4.35)

    async def _fetch_csv(self, series_id: str) -> float | None:
        url = _FRED_CSV_URL.format(series_id=series_id)
        r = await self._client.get(url)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        last_val: float | None = None
        for row in reader:
            if len(row) < 2 or row[0] == "DATE":
                continue
            v = row[1].strip()
            if v and v != ".":
                try:
                    last_val = float(v)
                except ValueError:
                    pass
        return last_val

    async def _fetch_api(self, series_id: str) -> float | None:
        params = {
            "series_id": series_id,
            "api_key": self._key,
            "file_type": "json",
            "limit": 5,
            "sort_order": "desc",
        }
        r = await self._client.get(_FRED_API_URL, params=params)
        r.raise_for_status()
        obs: list[dict[str, Any]] = r.json().get("observations", [])
        for o in obs:
            v = o.get("value", ".")
            if v and v != ".":
                try:
                    return float(v)
                except ValueError:
                    pass
        return None

    async def fetch_history(self, series_id: str = "DGS10", limit: int = 52) -> list[tuple[str, float]]:
        try:
            url = _FRED_CSV_URL.format(series_id=series_id)
            r = await asyncio.wait_for(self._client.get(url), timeout=8.0)
            r.raise_for_status()
            reader = csv.reader(io.StringIO(r.text))
            history: list[tuple[str, float]] = []
            for row in reader:
                if len(row) < 2 or row[0] == "DATE":
                    continue
                v = row[1].strip()
                if v and v != ".":
                    try:
                        history.append((row[0], float(v)))
                    except ValueError:
                        pass
            return history[-limit:]
        except Exception:
            today = datetime.today().strftime("%Y-%m-%d")
            return [(today, _KNOWN_RATES.get(series_id, 4.35))]

    async def aclose(self) -> None:
        await self._client.aclose()
