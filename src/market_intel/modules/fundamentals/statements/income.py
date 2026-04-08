from __future__ import annotations

from datetime import date

from market_intel.domain.entities.financial_statement import StatementLine, StatementType


def income_statement_lines(
    symbol: str,
    years: list[int],
    revenues: dict[int, float],
    net_income: dict[int, float],
    gross_profit: dict[int, float] | None = None,
    operating_income: dict[int, float] | None = None,
    ebitda: dict[int, float] | None = None,
) -> list[StatementLine]:
    lines: list[StatementLine] = []
    for y in years:
        fy = date(y, 12, 31)
        if y in revenues:
            lines.append(
                StatementLine(
                    label="Revenue",
                    concept="Revenues",
                    fiscal_period_end=fy,
                    value=revenues[y],
                    statement_type=StatementType.INCOME,
                )
            )
        if gross_profit and y in gross_profit:
            lines.append(
                StatementLine(
                    label="Gross Profit",
                    concept="GrossProfit",
                    fiscal_period_end=fy,
                    value=gross_profit[y],
                    statement_type=StatementType.INCOME,
                )
            )
        if operating_income and y in operating_income:
            lines.append(
                StatementLine(
                    label="Operating Income",
                    concept="OperatingIncomeLoss",
                    fiscal_period_end=fy,
                    value=operating_income[y],
                    statement_type=StatementType.INCOME,
                )
            )
        if ebitda and y in ebitda:
            lines.append(
                StatementLine(
                    label="EBITDA",
                    concept="EarningsBeforeInterestTaxesDepreciationAmortization",
                    fiscal_period_end=fy,
                    value=ebitda[y],
                    statement_type=StatementType.INCOME,
                )
            )
        if y in net_income:
            lines.append(
                StatementLine(
                    label="Net Income",
                    concept="NetIncomeLoss",
                    fiscal_period_end=fy,
                    value=net_income[y],
                    statement_type=StatementType.INCOME,
                )
            )
    return lines
