from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from market_intel.api.dependencies import get_portfolio_service
from market_intel.application.services.portfolio_service import PortfolioService
from market_intel.modules.portfolio.alpha_tracking import compute_alpha_series, generate_contextual_quiz

router = APIRouter(prefix="/portfolio", tags=["portfolio-alpha"])


@router.get("/alpha")
async def portfolio_alpha(
    start_value: float = 100_000.0,
    benchmark: str = "SPY",
    service: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, Any]:
    p = await service.load()
    snap = await service.snapshot(p)
    inception = p.updated_at or datetime.now(timezone.utc)
    alpha = await compute_alpha_series(
        portfolio_start_value=start_value,
        portfolio_current_value=float(snap.total_equity),
        portfolio_inception_date=inception,
        benchmark=benchmark,
    )
    return alpha


@router.get("/contextual-quiz")
async def contextual_quiz(
    service: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, Any]:
    p = await service.load()
    snap = await service.snapshot(p)
    positions = [pos.model_dump(mode="json") for pos in snap.positions]
    prices = {pos.symbol: (pos.last_price or 0.0) for pos in snap.positions}
    questions = generate_contextual_quiz(positions, prices)
    return {"questions": questions, "count": len(questions)}
