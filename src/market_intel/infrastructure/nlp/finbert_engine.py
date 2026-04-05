from __future__ import annotations

import asyncio
from functools import lru_cache

from market_intel.config.settings import Settings
from market_intel.domain.ports.sentiment_port import SentenceSentiment, SentimentPort


@lru_cache
def _sentiment_pipe(model_name: str):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    device = 0 if torch.cuda.is_available() else -1
    return pipeline(
        task="sentiment-analysis",
        model=model,
        tokenizer=tokenizer,
        device=device,
    )


class FinBertSentimentAdapter(SentimentPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _run_sync(self, sentences: list[str]) -> list[SentenceSentiment]:
        if not sentences:
            return []
        pipe = _sentiment_pipe(self._settings.finbert_model_name)
        results = pipe(sentences, truncation=True, max_length=512, top_k=3)
        if sentences and isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], dict):
                results = [results]
        out: list[SentenceSentiment] = []
        for text, res in zip(sentences, results, strict=True):
            pos = neg = neu = 0.0
            label = "neutral"
            best = 0.0
            items = res if isinstance(res, list) else [res]
            for item in items:
                lab = str(item["label"]).lower()
                score = float(item["score"])
                if lab == "positive":
                    pos = score
                elif lab == "negative":
                    neg = score
                elif lab == "neutral":
                    neu = score
                if score > best:
                    best = score
                    label = lab
            out.append(
                SentenceSentiment(
                    text=text,
                    label=label,
                    score_positive=pos,
                    score_negative=neg,
                    score_neutral=neu,
                )
            )
        return out

    async def score_sentences(self, sentences: list[str]) -> list[SentenceSentiment]:
        return await asyncio.to_thread(self._run_sync, sentences)
