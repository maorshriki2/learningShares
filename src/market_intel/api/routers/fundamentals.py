from __future__ import annotations

from fastapi import APIRouter, Depends

from market_intel.api.dependencies import get_fundamentals_service
from market_intel.application.services.fundamentals_service import FundamentalsService
from market_intel.infrastructure.market_data.instrument_info import last_price_and_shares
from market_intel.modules.fundamentals.education.dcf_explainer import margin_of_safety_note, summarize_dcf
from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, discounted_cash_flow_value

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])


def _fcf_from_dashboard(dashboard: object) -> float:
    for row in dashboard.cashflow:
        if row.label == "Free Cash Flow (derived)" and row.value is not None:
            return float(row.value)
    ocf = 0.0
    capex = 0.0
    for row in dashboard.cashflow:
        if row.label == "Operating Cash Flow" and row.value is not None:
            ocf = float(row.value)
        if row.label == "Capital Expenditures" and row.value is not None:
            capex = float(row.value)
    if ocf != 0.0:
        return max(ocf - abs(capex), 1.0)
    return 1.0


@router.get("/{symbol}/dashboard")
async def fundamentals_dashboard(
    symbol: str,
    years: int = 10,
    service: FundamentalsService = Depends(get_fundamentals_service),
) -> dict[str, object]:
    dto = await service.build_dashboard(symbol.upper(), years)
    return dto.model_dump(mode="json")


@router.post("/{symbol}/dcf/scenario")
async def dcf_scenario(
    symbol: str,
    body: dict[str, float],
    service: FundamentalsService = Depends(get_fundamentals_service),
) -> dict[str, object]:
    sym = symbol.upper()
    dashboard = await service.build_dashboard(sym, years=5)
    growth = float(body.get("growth", dashboard.dcf_base.growth_high))
    terminal = float(body.get("terminal_growth", dashboard.dcf_base.terminal_growth))
    wacc = float(body.get("wacc", dashboard.wacc))
    fcf_proxy = max(_fcf_from_dashboard(dashboard), 1.0)
    _px, shares = await last_price_and_shares(sym)

    res = discounted_cash_flow_value(
        DcfInputs(
            base_free_cash_flow=fcf_proxy,
            growth_years_1_to_5=growth,
            terminal_growth=terminal,
            wacc=max(wacc, 0.04),
        ),
        shares_outstanding=shares,
        net_debt=0.0,
    )
    summary = summarize_dcf(res, dashboard.market_price)
    return {
        "growth": growth,
        "terminal_growth": terminal,
        "wacc": wacc,
        "enterprise_value": res.enterprise_value,
        "intrinsic_per_share": res.implied_per_share,
        "summary": summary,
        "margin_of_safety_note": margin_of_safety_note(),
    }
