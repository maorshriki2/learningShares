"""Runtime smoke: final-verdict response shape (requires lifespan → use TestClient context manager)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from market_intel.api.main import app


def test_stock360_final_verdict_ok_and_schema() -> None:
    with TestClient(app) as client:
        r = client.get(
            "/api/v1/stock360/AAPL/final-verdict",
            params={"include_explain": "false"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    verdict = body.get("verdict") or {}
    probs = verdict.get("probabilities") or {}
    assert isinstance(probs, dict) and probs
    sample = next(iter(probs.values()))
    assert isinstance(sample, dict)
    for key in ("p_return_positive", "p_return_above_10pct", "p_return_below_-10pct"):
        assert key in sample
