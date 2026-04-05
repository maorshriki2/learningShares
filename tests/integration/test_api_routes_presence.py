from market_intel.api.main import app


def test_peers_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/peers/{symbol}" in paths


def test_macro_rates_route_is_registered() -> None:
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/macro/rates" in paths
