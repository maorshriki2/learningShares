from __future__ import annotations

from fastapi import APIRouter, Depends, Request

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.post("/finbert")
async def finbert_score(request: Request, body: dict[str, object]) -> dict[str, object]:
    state = request.app.state.app_state
    sentences = body.get("sentences")
    if not isinstance(sentences, list):
        raise ValueError("sentences must be a list")
    texts = [str(s) for s in sentences]
    scored = await state.finbert.score_sentences(texts)
    return {"results": [s.model_dump() for s in scored]}
