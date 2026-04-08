from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProcessedSignals:
    tags: list[str]
    category: str  # news|corporate|macro|rumors
    relevance: float


_TAG_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("[M&A]", re.compile(r"\b(acquire|acquisition|merger|m&a|takeover|buyout)\b", re.I)),
    ("[Earnings]", re.compile(r"\b(earnings|eps|guidance|quarter|q[1-4]\b|outlook)\b", re.I)),
    ("[Macro]", re.compile(r"\b(fed|powell|rates?|inflation|cpi|jobs|recession|yield|wacc)\b", re.I)),
    ("[Regulatory]", re.compile(r"\b(sec|doj|ftc|antitrust|regulator|probe|investigation)\b", re.I)),
    ("[Insider]", re.compile(r"\b(form\s*4|insider|sell(?:ing)?|buy(?:ing)?)\b", re.I)),
    ("[AI]", re.compile(r"\b(ai|artificial intelligence|llm|gpt|chip|gpu|nvidia)\b", re.I)),
]


def categorize_and_tag(text: str, *, source: str, tier: int) -> tuple[str, list[str]]:
    t = (text or "").strip()
    tags: list[str] = []
    for tag, rx in _TAG_RULES:
        if rx.search(t):
            tags.append(tag)

    # Coarse category routing
    if tier >= 3 or source.startswith("reddit"):
        return ("rumors", tags or ["[Rumor]"])
    if any(x == "[Macro]" for x in tags):
        return ("macro", tags)
    if any(x in ("[Earnings]", "[M&A]", "[Regulatory]", "[Insider]") for x in tags):
        return ("corporate", tags)
    return ("news", tags)


def time_decay_relevance(occurred_at: datetime | None, *, half_life_hours: float = 48.0) -> float:
    if occurred_at is None:
        return 0.55
    dt = occurred_at if occurred_at.tzinfo else occurred_at.replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    age_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
    if half_life_hours <= 0:
        return 1.0
    lam = math.log(2.0) / float(half_life_hours)
    score = math.exp(-lam * age_hours)
    return float(max(0.0, min(1.0, score)))

