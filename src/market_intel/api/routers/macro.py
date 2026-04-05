from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Request

from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, discounted_cash_flow_value
from market_intel.modules.fundamentals.valuation.wacc import WaccInputs, estimate_wacc
from market_intel.modules.macro.fred_adapter import FredRatesAdapter
from market_intel.modules.macro.wacc_simulation import RateScenario, ScenarioResult, simulate_wacc_rate_impact
from pydantic import BaseModel, Field

router = APIRouter(prefix="/macro", tags=["macro"])

_ADAPTER = FredRatesAdapter()


@router.get("/rates")
async def current_rates() -> dict[str, Any]:
    t10, t2, fed = await asyncio.gather(
        _ADAPTER.fetch_rate("DGS10"),
        _ADAPTER.fetch_rate("DGS2"),
        _ADAPTER.fetch_rate("DFF"),
    )
    return {
        "treasury_10y": round(t10, 4),
        "treasury_2y": round(t2, 4),
        "fed_funds": round(fed, 4),
        "source": "FRED (Federal Reserve Bank of St. Louis) or cached fallback",
    }


@router.get("/rates/history")
async def rate_history(series: str = "DGS10", limit: int = 52) -> dict[str, Any]:
    history = await _ADAPTER.fetch_history(series, limit=limit)
    return {
        "series": series,
        "data": [{"date": d, "value": v} for d, v in history],
    }


class WaccSimBody(BaseModel):
    current_risk_free: float = Field(default=0.0435, ge=0.0, le=0.25)
    equity_risk_premium: float = Field(default=0.055, ge=0.01, le=0.20)
    beta: float = Field(default=1.0, ge=0.0, le=5.0)
    cost_of_debt_pretax: float = Field(default=0.05, ge=0.005, le=0.25)
    tax_rate: float = Field(default=0.21, ge=0.0, le=0.50)
    equity_weight: float = Field(default=0.80, ge=0.01, le=1.0)
    debt_weight: float = Field(default=0.20, ge=0.0, le=0.99)
    base_fcf: float = Field(default=1_000_000_000.0, ge=1.0)
    growth: float = Field(default=0.05, ge=-0.20, le=0.50)
    terminal_growth: float = Field(default=0.02, ge=-0.05, le=0.10)
    shares_outstanding: float | None = Field(default=None, ge=1.0)
    net_debt: float = Field(default=0.0)
    rate_delta_from: float = Field(default=-3.0, ge=-10.0, le=0.0)
    rate_delta_to: float = Field(default=3.0, ge=0.0, le=10.0)
    rate_delta_step: float = Field(default=0.5, ge=0.1, le=2.0)


@router.post("/wacc-simulation")
async def wacc_simulation(body: WaccSimBody) -> dict[str, Any]:
    deltas = list(
        float(round(d, 3))
        for d in [
            body.rate_delta_from + i * body.rate_delta_step
            for i in range(int((body.rate_delta_to - body.rate_delta_from) / body.rate_delta_step) + 1)
        ]
    )
    scenario = RateScenario(
        risk_free_rate=body.current_risk_free,
        equity_risk_premium=body.equity_risk_premium,
        beta=body.beta,
        cost_of_debt_pretax=body.cost_of_debt_pretax,
        tax_rate=body.tax_rate,
        equity_weight=body.equity_weight,
        debt_weight=body.debt_weight,
        base_fcf=body.base_fcf,
        growth=body.growth,
        terminal_growth=body.terminal_growth,
        shares_outstanding=body.shares_outstanding,
        net_debt=body.net_debt,
    )
    results = simulate_wacc_rate_impact(scenario, rate_deltas=deltas)
    base_ev = next(
        (r.enterprise_value for r in results if abs(r.risk_free_rate - body.current_risk_free) < 0.001),
        results[len(results) // 2].enterprise_value if results else 1.0,
    )
    return {
        "scenarios": [
            {
                "rate_delta_pct": deltas[i],
                "risk_free_rate": round(r.risk_free_rate * 100, 3),
                "wacc": round(r.wacc * 100, 3),
                "cost_of_equity": round(r.cost_of_equity * 100, 3),
                "enterprise_value": round(r.enterprise_value, 0),
                "ev_change_pct": round((r.enterprise_value - base_ev) / max(base_ev, 1) * 100, 2),
                "implied_per_share": round(r.implied_per_share, 2) if r.implied_per_share else None,
            }
            for i, r in enumerate(results)
        ],
        "base_wacc_pct": round(
            estimate_wacc(
                WaccInputs(
                    cost_of_equity=body.current_risk_free + body.equity_risk_premium * body.beta,
                    cost_of_debt_after_tax=body.cost_of_debt_pretax * (1 - body.tax_rate),
                    equity_market_value=body.equity_weight,
                    debt_book_value=body.debt_weight,
                    tax_rate=body.tax_rate,
                )
            )
            * 100,
            3,
        ),
    }
