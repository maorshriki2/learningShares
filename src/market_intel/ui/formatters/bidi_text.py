"""Bidirectional text for Hebrew UI that mixes Latin tickers, acronyms, and API paths.

There is **no LLM / language model** involved: clarity comes from Unicode BiDi isolates
and (optionally) CSS ``direction`` / ``unicode-bidi`` so Latin stays LTR inside RTL Hebrew.

**Project rule (Streamlit Hebrew copy):** wrap English, acronyms, **numbers**, and **formulas** via
:func:`md_code` — HTML ``<bdi dir="ltr">`` + ``<code>`` so neutral punctuation stays LTR in RTL
pages. Call ``st.markdown`` / ``st.caption`` with ``unsafe_allow_html=True`` wherever ``md_code``
fragments are embedded.

Also available: :func:`ltr_embed`, :func:`num_embed` (Unicode isolates) when HTML spans are not used.

For long auto-generated strings, :func:`embed_latin_runs` / :func:`embed_numeric_runs` may still help.
"""

from __future__ import annotations

import html
import re

# Unicode bidi isolates: keep Latin runs left-to-right inside RTL paragraphs without
# scrambling order of adjacent Hebrew (common Streamlit/markdown pain on Windows/browser).
_LRI = "\u2066"  # LEFT-TO-RIGHT ISOLATE
_PDI = "\u2069"  # POP DIRECTIONAL ISOLATE

# Hebrew / Arabic runs inside an otherwise LTR UI (rare in this app).
_RLI = "\u2067"  # RIGHT-TO-LEFT ISOLATE

# Latin letter + common technical suffixes (tickers, paths, metric names).
_LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9._/:\-]*")

# Approximate counts like "~20" / "~ 87" (Hebrew UI).
_TILDE_COUNT = re.compile(r"~\s*\d+")
# Four-digit years (1900–2099) not part of a longer number.
_YEAR = re.compile(r"(?<![0-9])(?:19|20)\d{2}(?![0-9])")
# Percent literals in text e.g. 12.3% or +4.5%
_PERCENT = re.compile(r"[+\-]?\d+(?:\.\d+)?%")


def num_embed(value: str | int | float) -> str:
    """
    Wrap a numeric token (count, year, price, ``~20``, ``3.14%``) in LTR isolates.

    Use in Hebrew f-strings wherever digits sit next to Hebrew letters, e.g.::
        f"{num_embed(87)} ימים ב־{num_embed(2025)} לעומת …"
    """
    s = str(value).strip()
    if not s:
        return s
    return f"{_LRI}{s}{_PDI}"


def md_code(text: str | int | float) -> str:
    """
    LTR-isolated inline code for Streamlit (English, acronyms, numbers, formulas).

    Renders as ``<bdi dir="ltr"><code>…</code></bdi>``. Backticks inside ``text`` are replaced
    with an apostrophe. HTML-special characters in ``text`` are escaped for safe embedding.
    """
    inner = html.escape(str(text).replace("`", "'"), quote=False)
    return f'<bdi dir="ltr" style="white-space: nowrap;"><code>{inner}</code></bdi>'


def ltr_embed(text: str) -> str:
    """Wrap a Latin acronym, path, or English phrase so it renders LTR inside RTL text."""
    if not text:
        return text
    return f"{_LRI}{text}{_PDI}"


def rtl_embed(text: str) -> str:
    """Wrap a Hebrew snippet so it stays RTL inside an LTR paragraph (e.g. English-only page)."""
    if not text:
        return text
    return f"{_RLI}{text}{_PDI}"


def ltr_line(text: str) -> str:
    """Whole line/block that should read strictly LTR (e.g. one English sentence alone)."""
    return ltr_embed(text.strip())


def embed_latin_runs(text: str) -> str:
    """
    Wrap each contiguous Latin/technical run in LTR isolates.

    Handy for auto-built sentences; may still need manual ``ltr_embed`` for edge cases
    (numbers adjacent to Hebrew, mixed punctuation).
    """
    if not text:
        return text

    def repl(m: re.Match[str]) -> str:
        return ltr_embed(m.group(0))

    return _LATIN_RUN.sub(repl, text)


def embed_numeric_runs(text: str) -> str:
    """
    Auto-wrap common numeric patterns in LTR isolates inside Hebrew paragraphs.

    Does **not** handle comma-separated lists like ``30,90,365`` (pass those through explicit
    ``num_embed`` per segment or avoid this helper on that string).
    """
    if not text:
        return text

    def _sub(pat: re.Pattern[str], s: str) -> str:
        def repl(m: re.Match[str]) -> str:
            chunk = m.group(0).replace(" ", "").replace("\u00a0", "")
            return num_embed(chunk)

        return pat.sub(repl, s)

    out = _sub(_TILDE_COUNT, text)
    out = _sub(_YEAR, out)
    out = _PERCENT.sub(lambda m: num_embed(m.group(0)), out)
    return out


def embed_mixed_rtl(text: str) -> str:
    """Apply :func:`embed_numeric_runs` then :func:`embed_latin_runs` for mixed UI copy."""
    return embed_latin_runs(embed_numeric_runs(text))
