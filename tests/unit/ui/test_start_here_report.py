from market_intel.ui.components.start_here_report import collect_transparency_notes


def test_collect_transparency_notes_lists_failed_sources() -> None:
    data: dict = {"errors": ["טעינה נכשלה"], "macro": {}}
    notes = collect_transparency_notes(data)
    assert any("טעינה נכשלה" in n for n in notes)
    assert any("OHLCV" in n for n in notes)
    assert any("פונדמנטלים" in n for n in notes)


def test_collect_transparency_notes_detects_missing_indicator_values() -> None:
    data = {
        "errors": [],
        "payload_ohlcv": {"indicators": {"rsi14": [None], "macd": [], "macd_signal": []}},
        "payload_fundamentals": {
            "roic_latest": 0.1,
            "altman_z": 3.0,
            "margin_of_safety_pct": 5.0,
            "wacc": 0.09,
            "dcf_base": {"intrinsic_per_share": 100.0},
        },
        "payload_peers": {"rows": [{"is_subject": True, "symbol": "X"}], "sector_avg": {}},
        "macro": {"t10": 4.0, "t2": 3.5},
    }
    notes = collect_transparency_notes(data)
    assert any("RSI(14)" in n for n in notes)
