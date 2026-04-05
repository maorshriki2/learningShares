from __future__ import annotations

from typing import Any

import httpx


class MarketIntelApiClient:
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base, timeout=60.0)

    def health(self) -> dict[str, Any]:
        r = self._client.get("/api/v1/health")
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        s = (symbol or "").strip().upper()
        if not s:
            raise ValueError("Symbol cannot be empty.")
        return s

    def ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 300) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/market/{sym}/ohlcv",
            params={"timeframe": timeframe, "limit": limit},
        )
        r.raise_for_status()
        return r.json()

    def fundamentals_dashboard(self, symbol: str, years: int = 10) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(f"/api/v1/fundamentals/{sym}/dashboard", params={"years": years})
        r.raise_for_status()
        return r.json()

    def dcf_scenario(self, symbol: str, growth: float, terminal: float, wacc: float) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.post(
            f"/api/v1/fundamentals/{sym}/dcf/scenario",
            json={"growth": growth, "terminal_growth": terminal, "wacc": wacc},
        )
        r.raise_for_status()
        return r.json()

    def governance_dashboard(self, symbol: str, year: int, quarter: int) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/governance/{sym}/dashboard",
            params={"year": year, "quarter": quarter},
        )
        r.raise_for_status()
        return r.json()

    def analyst_narrative(self, symbol: str, year: int, quarter: int) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/governance/{sym}/analyst-narrative",
            params={"year": year, "quarter": quarter},
        )
        r.raise_for_status()
        return r.json()

    def portfolio(self) -> dict[str, Any]:
        r = self._client.get("/api/v1/portfolio/")
        r.raise_for_status()
        return r.json()

    def buy(self, symbol: str, quantity: float, price: float) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.post(
            "/api/v1/portfolio/buy",
            json={"symbol": sym, "quantity": quantity, "price": price},
        )
        r.raise_for_status()
        return r.json()

    def sell(self, symbol: str, quantity: float, price: float) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.post(
            "/api/v1/portfolio/sell",
            json={"symbol": sym, "quantity": quantity, "price": price},
        )
        r.raise_for_status()
        return r.json()

    def reset_portfolio(self) -> dict[str, Any]:
        r = self._client.post("/api/v1/portfolio/reset")
        r.raise_for_status()
        return r.json()

    def peer_comparison(self, symbol: str, extra: str = "") -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(f"/api/v1/peers/{sym}", params={"extra": extra})
        r.raise_for_status()
        return r.json()

    def macro_rates(self) -> dict[str, Any]:
        r = self._client.get("/api/v1/macro/rates")
        r.raise_for_status()
        return r.json()

    def macro_rate_history(self, series: str = "DGS10", limit: int = 104) -> dict[str, Any]:
        r = self._client.get("/api/v1/macro/rates/history", params={"series": series, "limit": limit})
        r.raise_for_status()
        return r.json()

    def macro_wacc_simulation(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/api/v1/macro/wacc-simulation", json=payload)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()
