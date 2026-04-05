from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PatternEducation:
    title: str
    psychology: str
    historical_note: str
    win_rate_context: str


def explain_pattern(pattern_name: str) -> PatternEducation:
    key = pattern_name.lower().strip()
    if key == "head_and_shoulders":
        return PatternEducation(
            title="Head and Shoulders (Bearish Reversal)",
            psychology=(
                "The pattern reflects exhaustion: a strong advance (left shoulder) is followed by a "
                "new high that fails to sustain (head), then a lower high (right shoulder) as buyers "
                "lose control. The neckline links reaction lows; a break signals a regime shift from "
                "demand-led to supply-led pricing as late longs capitulate."
            ),
            historical_note=(
                "Classical technical analysis treats this as a distribution structure: informed sellers "
                "unload into strength while retail participation peaks at the head."
            ),
            win_rate_context=(
                "Reported win rates in literature vary widely (roughly 65–85% for *pattern completion* "
                "after neckline breaks in academic backtests), heavily dependent on trend context, "
                "volume confirmation, and holding period. Use as a hypothesis, not a guarantee."
            ),
        )
    if key == "bull_flag":
        return PatternEducation(
            title="Bull Flag (Continuation)",
            psychology=(
                "A sharp rally (pole) expresses urgency and conviction. The flag is a pause where "
                "short-term holders take profits and late buyers wait; shallow pullbacks suggest "
                "supply is absorbed. Resolving upward implies the dominant buyers from the pole remain "
                "in control."
            ),
            historical_note=(
                "Continuation patterns are studied in momentum literature: impulse legs often cluster "
                "with information arrival; the flag represents lower-volatility consolidation before "
                "the next repricing leg."
            ),
            win_rate_context=(
                "Continuation setups in trend-following studies show moderate edge when combined with "
                "volume dynamics and broader market trend filters; isolated pattern win rates are not "
                "stable across assets and regimes."
            ),
        )
    return PatternEducation(
        title=pattern_name,
        psychology="No dedicated narrative is available for this pattern label.",
        historical_note="",
        win_rate_context="",
    )
