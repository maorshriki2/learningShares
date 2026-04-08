from fastapi.testclient import TestClient

from market_intel.api.main import app


def test_peers_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/peers/{symbol}" in paths


def test_macro_rates_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/macro/rates" in paths


def test_governance_analyst_narrative_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/governance/{symbol}/analyst-narrative" in paths
    assert "/api/v1/governance/{symbol}/dashboard" in paths


def test_governance_analyst_narrative_returns_200_json() -> None:
    """Empty/invalid Finnhub JSON must not surface as HTTP 400 (JSONDecodeError → ValueError)."""
    with TestClient(app) as client:
        r = client.get(
            "/api/v1/governance/DUOL/analyst-narrative",
            params={"year": 2024, "quarter": 4},
        )
    assert r.status_code == 200
    body = r.json()
    assert "ok" in body
    assert "message_he" in body


def test_watchlist_sector_buckets_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/watchlist/sector-buckets" in paths


def test_stock360_final_verdict_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/stock360/{symbol}/final-verdict" in paths


def test_valuation_verdict_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/valuation/{symbol}/verdict" in paths


def test_market_context_feed_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/market/{symbol}/context-feed" in paths


def test_blindtest_analyze_scenario_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/blindtest/analyze-scenario" in paths
