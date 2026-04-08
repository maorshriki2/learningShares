from __future__ import annotations

from typing import Any

import httpx

from market_intel.ui.state.session import normalize_api_public_url, resolve_symbol_for_api


class MarketIntelApiClient:
    def __init__(self, base_url: str, *, normalize_symbol: bool = True) -> None:
        self._base = normalize_api_public_url(base_url)
        self._client = httpx.Client(base_url=self._base, timeout=60.0)
        self._normalize_symbols = bool(normalize_symbol)

    @staticmethod
    def _api_error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("detail") is not None:
                return str(body["detail"])
        except (ValueError, TypeError):
            pass
        text = (response.text or "").strip()
        return text[:1200] if text else response.reason_phrase or "Request failed"

    def health(self) -> dict[str, Any]:
        r = self._client.get("/api/v1/health")
        r.raise_for_status()
        return r.json()

    def _normalize_symbol(self, symbol: str) -> str:
        if not self._normalize_symbols:
            return (symbol or "").strip().upper()
        return resolve_symbol_for_api(symbol)

    def ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 300) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/market/{sym}/ohlcv",
            params={"timeframe": timeframe, "limit": limit},
        )
        r.raise_for_status()
        return r.json()

    def market_context_feed(self, symbol: str) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(f"/api/v1/market/{sym}/context-feed")
        r.raise_for_status()
        return r.json()

    def fundamentals_dashboard(self, symbol: str, years: int = 10) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(f"/api/v1/fundamentals/{sym}/dashboard", params={"years": years})
        r.raise_for_status()
        return r.json()

    def dcf_scenario(
        self, symbol: str, growth: float, terminal: float, wacc: float
    ) -> dict[str, Any]:
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
        if r.is_error:
            msg = self._api_error_message(r)
            raise httpx.HTTPStatusError(
                f"{r.status_code} {msg}",
                request=r.request,
                response=r,
            )
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

    def instrument_summary(self, symbol: str) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(f"/api/v1/instruments/{sym}/summary")
        r.raise_for_status()
        return r.json()

    def macro_rates(self) -> dict[str, Any]:
        r = self._client.get("/api/v1/macro/rates")
        r.raise_for_status()
        return r.json()

    def macro_rate_history(self, series: str = "DGS10", limit: int = 104) -> dict[str, Any]:
        r = self._client.get(
            "/api/v1/macro/rates/history",
            params={"series": series, "limit": limit},
        )
        r.raise_for_status()
        return r.json()

    def macro_wacc_simulation(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/api/v1/macro/wacc-simulation", json=payload)
        r.raise_for_status()
        return r.json()

    def analysis_artifact(
        self,
        symbol: str,
        *,
        include_explain: bool = True,
        timeframe: str = "1d",
        limit: int = 320,
        years: int = 10,
        gov_year: int = 2024,
        gov_quarter: int = 4,
        peers_extra: str = "",
        mos_required: float = 0.15,
        premium_threshold: float = 0.15,
        wacc_span: float = 0.02,
        terminal_span: float = 0.01,
        grid_size: int = 5,
    ) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/analysis/{sym}/artifact",
            params={
                "include_explain": "true" if include_explain else "false",
                "timeframe": timeframe,
                "limit": int(limit),
                "years": int(years),
                "gov_year": int(gov_year),
                "gov_quarter": int(gov_quarter),
                "peers_extra": str(peers_extra or ""),
                "mos_required": float(mos_required),
                "premium_threshold": float(premium_threshold),
                "wacc_span": float(wacc_span),
                "terminal_span": float(terminal_span),
                "grid_size": int(grid_size),
            },
        )
        r.raise_for_status()
        return r.json()

    def stock360_bundle(
        self,
        symbol: str,
        *,
        timeframe: str = "1d",
        limit: int = 320,
        years: int = 10,
        gov_year: int = 2024,
        gov_quarter: int = 4,
        include_explain: bool = True,
    ) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/stock360/{sym}/bundle",
            params={
                "timeframe": timeframe,
                "limit": limit,
                "years": years,
                "gov_year": gov_year,
                "gov_quarter": gov_quarter,
                "include_explain": include_explain,
            },
        )
        r.raise_for_status()
        return r.json()

    def stock360_final_verdict(
        self,
        symbol: str,
        *,
        horizon_days: list[int] | None = None,
        include_explain: bool = True,
    ) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        params: list[tuple[str, str]] = [("include_explain", "true" if include_explain else "false")]
        if horizon_days:
            params.append(("horizon_days", ",".join(str(int(x)) for x in horizon_days)))
        r = self._client.get(f"/api/v1/stock360/{sym}/final-verdict", params=params)
        r.raise_for_status()
        return r.json()

    def blind_analyze_scenario(
        self,
        study: dict[str, Any],
        *,
        horizon_days: str = "30,90,365",
        include_explain: bool = True,
    ) -> dict[str, Any]:
        r = self._client.post(
            "/api/v1/blindtest/analyze-scenario",
            json={
                "study": study,
                "horizon_days": horizon_days,
                "include_explain": include_explain,
            },
        )
        r.raise_for_status()
        return r.json()

    def watchlist_sector_buckets(
        self,
        *,
        sectors: list[str] | None = None,
        large_n: int = 5,
        mid_n: int = 5,
        small_n: int = 5,
    ) -> dict[str, Any]:
        params: list[tuple[str, str]] = []
        for s in sectors or []:
            ss = (s or "").strip()
            if ss:
                params.append(("sectors", ss))
        params.extend(
            [
                ("large_n", str(int(large_n))),
                ("mid_n", str(int(mid_n))),
                ("small_n", str(int(small_n))),
            ]
        )
        r = self._client.get("/api/v1/watchlist/sector-buckets", params=params)
        r.raise_for_status()
        return r.json()

    def valuation_verdict(
        self,
        symbol: str,
        *,
        years: int = 10,
        include_explain: bool = True,
        mos_required: float = 0.15,
        premium_threshold: float = 0.15,
        wacc_span: float = 0.02,
        terminal_span: float = 0.01,
        grid_size: int = 5,
    ) -> dict[str, Any]:
        sym = self._normalize_symbol(symbol)
        r = self._client.get(
            f"/api/v1/valuation/{sym}/verdict",
            params={
                "years": int(years),
                "include_explain": "true" if include_explain else "false",
                "mos_required": float(mos_required),
                "premium_threshold": float(premium_threshold),
                "wacc_span": float(wacc_span),
                "terminal_span": float(terminal_span),
                "grid_size": int(grid_size),
            },
        )
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()
