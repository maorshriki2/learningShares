from typing import Protocol

from market_intel.domain.entities.financial_statement import StatementLine, StatementType


class FundamentalsPort(Protocol):
    async def get_statement_series(
        self,
        symbol: str,
        statement_type: StatementType,
        years: int,
    ) -> list[StatementLine]: ...
