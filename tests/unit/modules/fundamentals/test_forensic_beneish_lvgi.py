"""Beneish LVGI fallback when long-term debt tags are missing from XBRL."""

from market_intel.modules.fundamentals.forensics.forensic_analyzer import _beneish_m_score


def test_beneish_completes_with_total_liabilities_when_ltd_and_cl_missing() -> None:
    t, t1 = 2024, 2023
    sales = {t: 100.0, t1: 90.0}
    rec = {t: 10.0, t1: 9.0}
    cogs = {t: 40.0, t1: 36.0}
    ca = {t: 50.0, t1: 48.0}
    ppe = {t: 30.0, t1: 28.0}
    ta = {t: 200.0, t1: 190.0}
    dep = {t: 5.0, t1: 4.0}
    sga = {t: 20.0, t1: 18.0}
    ni = {t: 15.0, t1: 14.0}
    ocf = {t: 14.0, t1: 13.0}
    m, err, note, explain = _beneish_m_score(
        t,
        t1,
        sales,
        rec,
        cogs,
        ca,
        ppe,
        ta,
        dep,
        sga,
        ni,
        ocf,
        ltd={},
        cl={},
        total_liab={t: 120.0, t1: 110.0},
    )
    assert err is None
    assert m is not None
    assert note is not None
    assert "LVGI" in note
    assert isinstance(explain, dict)
