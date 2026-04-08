from market_intel.ui.state.session import is_placeholder_symbol, PLACEHOLDER_SYMBOLS


def test_anony_is_placeholder() -> None:
    assert is_placeholder_symbol("anony")
    assert is_placeholder_symbol("ANONY")
    assert "ANONY" in PLACEHOLDER_SYMBOLS


def test_real_tickers_not_placeholder() -> None:
    assert not is_placeholder_symbol("AAPL")
    assert not is_placeholder_symbol("MSFT")
