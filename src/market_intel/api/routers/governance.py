from __future__ import annotations

from fastapi import APIRouter, Depends

from market_intel.api.dependencies import get_governance_service
from market_intel.application.services.governance_service import GovernanceService

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/{symbol}/analyst-narrative")
async def governance_analyst_narrative(
    symbol: str,
    year: int = 2024,
    quarter: int = 4,
    service: GovernanceService = Depends(get_governance_service),
) -> dict[str, object]:
    """Keep literal path `analyst-narrative` registered with a predictable order."""
    return await service.analyst_narrative(symbol.strip().upper(), year, quarter)


@router.get("/{symbol}/dashboard")
async def governance_dashboard(
    symbol: str,
    year: int = 2024,
    quarter: int = 4,
    service: GovernanceService = Depends(get_governance_service),
) -> dict[str, object]:
    dto = await service.build_dashboard(symbol.strip().upper(), year, quarter)
    return dto.model_dump(mode="json")
