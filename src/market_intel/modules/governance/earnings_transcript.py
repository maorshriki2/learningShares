from __future__ import annotations

import re

from market_intel.domain.ports.transcript_port import EarningsTranscript, TranscriptUtterance


def split_into_sentences(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 0]


def utterances_from_plaintext(
    symbol: str,
    year: int,
    quarter: int,
    speaker: str,
    body: str,
    source: str,
) -> EarningsTranscript:
    sents = split_into_sentences(body)
    utt = [
        TranscriptUtterance(speaker=speaker, text=s, sequence=i) for i, s in enumerate(sents)
    ]
    return EarningsTranscript(
        symbol=symbol,
        year=year,
        quarter=quarter,
        source=source,
        utterances=utt,
    )
