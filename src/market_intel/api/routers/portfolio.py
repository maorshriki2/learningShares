from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from market_intel.api.dependencies import get_portfolio_service
from market_intel.application.services.portfolio_service import PortfolioService
from market_intel.domain.entities.portfolio import Portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class TradeBody(BaseModel):
    symbol: str
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


@router.get("/")
async def get_portfolio(service: PortfolioService = Depends(get_portfolio_service)) -> dict[str, object]:
    p = await service.load()
    snap = await service.snapshot(p)
    return snap.model_dump(mode="json")


@router.post("/buy")
async def buy(
    body: TradeBody,
    service: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, object]:
    p = await service.buy(body.symbol, body.quantity, body.price)
    snap = await service.snapshot(p)
    return snap.model_dump(mode="json")


@router.post("/sell")
async def sell(
    body: TradeBody,
    service: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, object]:
    p = await service.sell(body.symbol, body.quantity, body.price)
    snap = await service.snapshot(p)
    return snap.model_dump(mode="json")


@router.post("/reset")
async def reset(service: PortfolioService = Depends(get_portfolio_service)) -> dict[str, object]:
    fresh = Portfolio(cash_usd=Decimal("100000"), positions={})
    await service.save(fresh)
    snap = await service.snapshot(fresh)
    return snap.model_dump(mode="json")
