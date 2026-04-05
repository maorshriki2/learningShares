from __future__ import annotations

from market_intel.domain.ports.sentiment_port import SentimentPort
from market_intel.domain.ports.transcript_port import EarningsTranscript, TranscriptPort
from market_intel.infrastructure.nlp.sentence_highlight import top_bullish_bearish


async def analyze_earnings_transcript(
    transcripts: TranscriptPort,
    sentiment: SentimentPort,
    symbol: str,
    year: int,
    quarter: int,
) -> tuple[EarningsTranscript | None, object, object]:
    tr = await transcripts.fetch_transcript(symbol, year, quarter)
    if not tr:
        return None, [], []
    sentences = [u.text for u in tr.utterances if u.text][:60]
    scored = await sentiment.score_sentences(sentences)
    bull, bear = top_bullish_bearish(scored, k=6)
    return tr, bull, bear
