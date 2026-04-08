from __future__ import annotations

from market_intel.ui.components.research_story_panel import build_expert_analysis_paragraphs_he, build_red_flag_lines_he


def test_red_flags_from_mos_roic_without_forensic_dup() -> None:
    dash = {
        "margin_of_safety_pct": -36.7,
        "roic_latest": -0.0222,
        "wacc": 0.10,
        "piotroski_score": 5,
        "altman_z": 0.9,
        "forensic_flags": [],
    }
    lines = build_red_flag_lines_he(
        dash=dash,
        verdict=None,
        study_financials=None,
        include_forensic_duplicates=False,
    )
    assert len(lines) >= 3
    blob = "\n".join(lines)
    assert "<code>MOS</code>" in blob and "<code>ROIC</code>" in blob
    assert 'dir="ltr"' in blob


def test_expert_stress_branch() -> None:
    dash = {"margin_of_safety_pct": -20, "roic_latest": 0.01, "wacc": 0.1}
    verdict = {"fundamental_stress_active": True, "forecast_direction_ml_raw": "up", "forecast_direction": "down_or_flat"}
    parts = build_expert_analysis_paragraphs_he(dash=dash, verdict=verdict)
    blob = "\n".join(parts)
    assert "מודל" in blob
