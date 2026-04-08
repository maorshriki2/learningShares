"""Tests for educational fundamental stress fusion (blind / distressed cases)."""

from __future__ import annotations

from market_intel.modules.analytics.fundamental_stress_fusion import (
    apply_fundamental_stress_fusion,
    fundamental_stress_bearish,
)


def test_fundamental_stress_bearish_enron_like() -> None:
    fund = {
        "roic_latest": 0.0153,
        "wacc": 0.10,
        "margin_of_safety_pct": -25.4,
        "altman_z": 0.78,
        "piotroski_score": 2,
        "forensic_flags": [
            {"severity": "high", "title_he": "Altman"},
        ],
    }
    bearish, reasons = fundamental_stress_bearish(fund)
    assert bearish is True
    assert len(reasons) >= 3


def test_apply_fusion_overrides_up_to_down_or_flat() -> None:
    fund = {
        "roic_latest": 0.015,
        "wacc": 0.10,
        "margin_of_safety_pct": -30.0,
        "altman_z": 0.5,
        "piotroski_score": 2,
        "forensic_flags": [{"severity": "high"}],
    }
    verdict = {
        "forecast_direction": "up",
        "probabilities": {
            "90d": {"p_return_positive": 0.7, "p_return_below_-10pct": 0.1},
        },
    }
    apply_fundamental_stress_fusion(verdict, fund)
    assert verdict.get("fundamental_stress_active") is True
    assert verdict.get("forecast_direction") == "down_or_flat"
    assert verdict.get("forecast_direction_ml_raw") == "up"
    p90 = verdict["probabilities"]["90d"]
    assert float(p90["p_return_positive"]) <= 0.33


def test_altman_mos_backup_without_piotroski() -> None:
    """When piotroski is missing, Altman risk + deep negative MOS still flags stress."""
    fund = {
        "roic_latest": 0.08,
        "wacc": 0.09,
        "margin_of_safety_pct": -25.0,
        "altman_z": 0.78,
        "piotroski_score": None,
        "forensic_flags": [],
    }
    bearish, reasons = fundamental_stress_bearish(fund)
    assert bearish is True
    assert any("Piotroski" in r or "Altman" in r for r in reasons)


def test_no_fusion_when_healthy() -> None:
    fund = {
        "roic_latest": 0.12,
        "wacc": 0.09,
        "margin_of_safety_pct": 20.0,
        "altman_z": 3.5,
        "piotroski_score": 7,
        "forensic_flags": [],
    }
    verdict = {"forecast_direction": "up", "probabilities": {}}
    apply_fundamental_stress_fusion(verdict, fund)
    assert verdict.get("fundamental_stress_active") is False
    assert verdict.get("forecast_direction") == "up"
