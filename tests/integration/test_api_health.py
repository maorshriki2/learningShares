from fastapi.testclient import TestClient

from market_intel.api.main import app


def test_health() -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
