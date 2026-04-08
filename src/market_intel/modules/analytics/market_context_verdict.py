from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_market_context_verdict(*, symbol: str, feed: dict[str, Any] | None) -> dict[str, Any]:
    """
    Minimal, fail-soft verdict from `market_context_feed`.
    For now:
    - If the rumors section has `ai_verdict`, translate it into bullish/bearish/neutral.
    - Otherwise return not_ready/neutral with explanations.
    """
    sym = (symbol or "").strip().upper()
    now = datetime.now(timezone.utc).isoformat()

    if not isinstance(feed, dict) or not feed.get("ok", True):
        return {
            "ok": True,
            "symbol": sym,
            "fetched_at_utc": now,
            "signal": "not_ready",
            "confidence": None,
            "key_points_he": [],
            "risks_he": ["שכבת הקשר שוק לא זמינה כרגע (feed לא תקין)."],
            "explain": {"reason": "feed_missing_or_not_ok"},
        }

    sections = feed.get("sections")
    rumors = None
    news = None
    if isinstance(sections, list):
        for s in sections:
            if isinstance(s, dict) and str(s.get("id") or "") == "rumors":
                rumors = s
            if isinstance(s, dict) and str(s.get("id") or "") == "news":
                news = s

    ai_verdict = str((rumors or {}).get("ai_verdict") or "").strip().lower()
    bottom = str((rumors or {}).get("ai_bottom_line_he") or "").strip()

    signal = "not_ready"
    if ai_verdict == "bullish":
        signal = "bullish"
    elif ai_verdict == "bearish":
        signal = "bearish"
    elif ai_verdict in ("mixed", "neutral"):
        signal = "neutral"

    points: list[str] = []
    if bottom:
        points.append(bottom)

    # Fallback: derive a soft signal from item sentiments (news+rumors) if AI is missing.
    def _sentiment_score(section: dict[str, Any] | None) -> tuple[float, int]:
        items = (section or {}).get("items")
        if not isinstance(items, list) or not items:
            return 0.0, 0
        acc = 0.0
        n = 0
        for it in items[:25]:
            if not isinstance(it, dict):
                continue
            lab = str(it.get("sentiment_label") or "").lower()
            sc = it.get("sentiment_score")
            rel = it.get("relevance")
            try:
                w = float(rel) if rel is not None else 0.5
            except Exception:
                w = 0.5
            try:
                v = float(sc) if sc is not None else None
            except Exception:
                v = None
            if v is None:
                # map label to a small default score
                if lab == "positive":
                    v = 0.25
                elif lab == "negative":
                    v = -0.25
                else:
                    v = 0.0
            # clamp
            v = max(-1.0, min(1.0, float(v)))
            acc += v * max(0.05, min(1.0, w))
            n += 1
        return (acc / max(1, n)), n

    s_rum, n_rum = _sentiment_score(rumors)
    s_news, n_news = _sentiment_score(news)
    s_blend = (s_rum * 0.6 + s_news * 0.4) if (n_rum + n_news) > 0 else 0.0

    if signal == "not_ready" and (n_rum + n_news) >= 6:
        if s_blend >= 0.12:
            signal = "bullish"
        elif s_blend <= -0.12:
            signal = "bearish"
        else:
            signal = "neutral"

    items = (rumors or {}).get("items")
    n_items = len(items) if isinstance(items, list) else 0
    risks: list[str] = []
    if signal == "not_ready":
        if n_items > 0:
            risks.append("יש פוסטים גולמיים אך אין עדיין סיכום AI שמייצר סיגנל.")
        else:
            risks.append("אין מספיק פריטים בשכבת הרשת כדי להפיק סיגנל.")

    return {
        "ok": True,
        "symbol": sym,
        "fetched_at_utc": now,
        "signal": signal,
        "confidence": None,
        "key_points_he": points,
        "risks_he": risks,
        "explain": {
            "rumors_ai_verdict": ai_verdict or None,
            "rumors_items_n": int(n_items),
            "sentiment_fallback": {
                "rumors_avg": float(s_rum),
                "rumors_n": int(n_rum),
                "news_avg": float(s_news),
                "news_n": int(n_news),
                "blend": float(s_blend),
            },
            "sources_attempted": feed.get("sources_attempted"),
            "errors": feed.get("errors"),
        },
    }

