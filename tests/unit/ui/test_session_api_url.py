from market_intel.ui.state.session import normalize_api_public_url


def test_normalize_api_public_url_strips_trailing_api_v1() -> None:
    assert normalize_api_public_url("http://127.0.0.1:8000/api/v1") == "http://127.0.0.1:8000"
    assert normalize_api_public_url("http://127.0.0.1:8000/API/V1") == "http://127.0.0.1:8000"


def test_normalize_api_public_url_preserves_plain_origin() -> None:
    assert normalize_api_public_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert normalize_api_public_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
