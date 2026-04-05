from __future__ import annotations

from market_intel.domain.ports.sentiment_port import SentenceSentiment


def corporate_speak_lesson(highlights: list[SentenceSentiment]) -> str:
    base = (
        "Earnings calls blend operational facts with strategic framing. "
        "Hedged language ('cautiously optimistic', 'headwinds', 'mixed') often signals uncertainty. "
        "FinBERT scores sentences for financial tone, but always read the full paragraph for "
        "numeric guidance and second-order effects.\n\n"
    )
    if not highlights:
        return base + "No highlighted sentences in this sample."
    bullets = []
    for h in highlights[:8]:
        label = h.label.upper()
        snippet = h.text[:220] + ("…" if len(h.text) > 220 else "")
        bullets.append(f"- [{label}] {snippet}")
    return base + "Highlighted fragments:\n" + "\n".join(bullets)
