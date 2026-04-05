from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from market_intel.modules.blind_test.case_study_engine import CaseStudyEngine

router = APIRouter(prefix="/blindtest", tags=["blind-test"])

_engine = CaseStudyEngine()


@router.get("/list")
async def list_studies() -> dict[str, Any]:
    return {"ids": _engine.list_ids()}


@router.get("/random")
async def random_study() -> dict[str, Any]:
    sid = _engine.random_id()
    return _engine.get_blind(sid)


@router.get("/{study_id}/blind")
async def blind_study(study_id: str) -> dict[str, Any]:
    return _engine.get_blind(study_id)


class RevealBody(BaseModel):
    decision: str
    explanation: str = ""


@router.post("/{study_id}/reveal")
async def reveal_study(study_id: str, body: RevealBody) -> dict[str, Any]:
    return _engine.get_reveal(study_id, body.decision, body.explanation)
