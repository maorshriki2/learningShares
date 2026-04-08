"""
Reusable “focus” panels for Hebrew explanations: color accent, RTL, formulas on their own row.

Use across Streamlit narratives so copy stays **line-broken**, **ticker-aware**, and visually scannable.
"""

from __future__ import annotations

import html
import re
from typing import Literal

import streamlit as st

from market_intel.ui.formatters.bidi_text import md_code

_VARIANT_CLASS: dict[str, str] = {
    "insight": "mi-focus-insight",
    "caution": "mi-focus-caution",
    "steps": "mi-focus-steps",
    "neutral": "mi-focus-neutral",
}

_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_BDI_CHUNK = re.compile(r"(<bdi\b[\s\S]*?</bdi>)")


def formula_row(text: str | int | float) -> str:
    """LTR formula / code on its own visual row (uses :func:`md_code`)."""
    return f'<div class="mi-formula-row">{md_code(text)}</div>'


def _bold_to_strong(segment: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return "<strong>" + html.escape(m.group(1), quote=False) + "</strong>"

    return _BOLD.sub(repl, segment)


def _body_to_html(body: str) -> str:
    """Turn newlines into <br>; convert **bold** only outside existing HTML chunks (e.g. ``md_code``)."""
    s = body.replace("\n\n", "<br><br>").replace("\n", "<br>")
    parts = re.split(_BDI_CHUNK, s)
    out: list[str] = []
    for part in parts:
        if part.startswith("<bdi"):
            out.append(part)
        else:
            out.append(_bold_to_strong(part))
    return "".join(out)


def render_focus_block(
    body: str,
    *,
    variant: Literal["insight", "caution", "steps", "neutral"] = "neutral",
) -> None:
    """
    Single explanation panel. ``body`` may mix Hebrew, ``**bold**``, and HTML from :func:`md_code` / :func:`formula_row`.
    """
    vc = _VARIANT_CLASS.get(variant, "mi-focus-neutral")
    inner = _body_to_html(body)
    st.markdown(
        f'<div class="mi-focus {vc}"><div class="mi-focus-inner">{inner}</div></div>',
        unsafe_allow_html=True,
    )


def render_focus_heading(label: str, *, variant: Literal["insight", "caution", "steps", "neutral"] = "steps") -> None:
    """Short heading strip above a sequence of focus blocks (same palette)."""
    vc = _VARIANT_CLASS.get(variant, "mi-focus-steps")
    inner = _body_to_html(label)
    st.markdown(
        f'<div class="mi-focus-heading {vc}">{inner}</div>',
        unsafe_allow_html=True,
    )
