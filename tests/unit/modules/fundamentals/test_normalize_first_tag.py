from market_intel.modules.fundamentals.xbrl.normalize_statements import annual_series_first_matching_tag


def test_annual_series_first_matching_tag_empty_facts() -> None:
    assert annual_series_first_matching_tag({}, "us-gaap", ("Revenues",)) == {}
