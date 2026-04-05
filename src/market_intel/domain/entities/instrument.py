from pydantic import BaseModel, Field

from market_intel.domain.value_objects.sector import Sector
from market_intel.domain.value_objects.symbol import Symbol


class Instrument(BaseModel):
    symbol: Symbol
    name: str = ""
    exchange: str = ""
    sector: Sector = Sector.UNKNOWN
    beta: float | None = None
