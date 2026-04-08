from __future__ import annotations

from market_intel.ui.components.blind_csv_io import blind_study_from_csv_bytes, blind_study_to_csv_bytes


def test_csv_roundtrip_preserves_data_and_anony_on_import() -> None:
    study = {
        "id": "cs_001",
        "codename": "Company A",
        "year": 2007,
        "sector": "Financial Services",
        "price_at_snapshot": 58.0,
        "financials_summary": {
            "revenue_b": 59.0,
            "net_income_b": 4.2,
            "total_assets_b": 691.0,
            "pe_ratio": 13.8,
            "debt_to_equity": 30.7,
            "operating_cashflow_b": -14.0,
        },
        "piotroski_score": 3,
        "altman_z": 0.62,
        "altman_zone": "danger",
        "price_chart_data": [
            {"offset_months": 0, "price_factor": 1.0},
            {"offset_months": 12, "price_factor": 0.5},
        ],
    }
    raw = blind_study_to_csv_bytes(study)
    loaded = blind_study_from_csv_bytes(raw)
    assert loaded["codename"] == "anony"
    assert loaded["year"] == 2007
    assert loaded["sector"] == "Financial Services"
    assert loaded["price_at_snapshot"] == 58.0
    assert loaded["piotroski_score"] == 3
    assert loaded["altman_z"] == 0.62
    assert len(loaded["price_chart_data"]) == 2
    assert loaded["financials_summary"]["pe_ratio"] == 13.8
