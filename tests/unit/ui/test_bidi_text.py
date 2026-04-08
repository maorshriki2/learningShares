from market_intel.ui.formatters.bidi_text import (
    embed_latin_runs,
    embed_numeric_runs,
    ltr_embed,
    md_code,
    num_embed,
    rtl_embed,
)


def test_ltr_embed_wraps_isolates() -> None:
    s = ltr_embed("ROIC")
    assert "\u2066" in s
    assert "ROIC" in s
    assert "\u2069" in s


def test_embed_latin_runs_multiple_tokens() -> None:
    s = embed_latin_runs("ROIC נמוך מ-WACC ב-API")
    assert "\u2066" in s
    assert "ROIC" in s
    assert "WACC" in s
    assert "API" in s


def test_rtl_embed() -> None:
    s = rtl_embed("עברית")
    assert "\u2067" in s


def test_num_embed_days_year_example() -> None:
    """Reading order: count, then 'ימים', then year (LTR isolates keep digits stable)."""
    s = f"{num_embed(87)} ימים ב־{num_embed(2025)} לעומת"
    assert "\u2066" in s
    assert "87" in s
    assert "2025" in s


def test_md_code_bdi_ltr_and_escapes() -> None:
    assert md_code("DSO") == (
        '<bdi dir="ltr" style="white-space: nowrap;"><code>DSO</code></bdi>'
    )
    assert md_code("a`b") == (
        '<bdi dir="ltr" style="white-space: nowrap;"><code>a\'b</code></bdi>'
    )
    assert "&lt;" in md_code("<tag>")


def test_embed_numeric_runs_tilde_and_year() -> None:
    s = embed_numeric_runs("ממוצע על ~20 תצפיות ב־2025")
    assert "\u2066" in s
    assert "2025" in s
    assert "20" in s
