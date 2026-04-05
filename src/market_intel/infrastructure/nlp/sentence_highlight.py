from __future__ import annotations

from market_intel.domain.ports.sentiment_port import SentenceSentiment


def top_bullish_bearish(
    scored: list[SentenceSentiment],
    k: int = 5,
) -> tuple[list[SentenceSentiment], list[SentenceSentiment]]:
    bullish = sorted(
        scored,
        key=lambda s: s.score_positive - max(s.score_negative, s.score_neutral),
        reverse=True,
    )[:k]
    bearish = sorted(
        scored,
        key=lambda s: s.score_negative - max(s.score_positive, s.score_neutral),
        reverse=True,
    )[:k]
    return bullish, bearish
