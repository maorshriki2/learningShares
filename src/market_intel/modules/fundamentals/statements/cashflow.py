from __future__ import annotations

from datetime import date

from market_intel.domain.entities.financial_statement import StatementLine, StatementType


def cashflow_lines(
    symbol: str,
    years: list[int],
    operating_cashflow: dict[int, float],
    capex: dict[int, float] | None = None,
    free_cash_flow: dict[int, float] | None = None,
) -> list[StatementLine]:
    lines: list[StatementLine] = []
    for y in years:
        fy = date(y, 12, 31)
        if y in operating_cashflow:
            lines.append(
                StatementLine(
                    label="Operating Cash Flow",
                    concept="NetCashProvidedByUsedInOperatingActivities",
                    fiscal_period_end=fy,
                    value=operating_cashflow[y],
                    statement_type=StatementType.CASHFLOW,
                )
            )
        if capex and y in capex:
            lines.append(
                StatementLine(
                    label="Capital Expenditures",
                    concept="PaymentsToAcquirePropertyPlantAndEquipment",
                    fiscal_period_end=fy,
                    value=capex[y],
                    statement_type=StatementType.CASHFLOW,
                )
            )
        if free_cash_flow and y in free_cash_flow:
            lines.append(
                StatementLine(
                    label="Free Cash Flow (derived)",
                    concept="FreeCashFlowDerived",
                    fiscal_period_end=fy,
                    value=free_cash_flow[y],
                    statement_type=StatementType.CASHFLOW,
                )
            )
    return lines
