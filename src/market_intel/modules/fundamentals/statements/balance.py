from __future__ import annotations

from datetime import date

from market_intel.domain.entities.financial_statement import StatementLine, StatementType


def balance_sheet_lines(
    symbol: str,
    years: list[int],
    total_assets: dict[int, float],
    total_liabilities: dict[int, float],
    equity: dict[int, float] | None = None,
    current_assets: dict[int, float] | None = None,
    current_liabilities: dict[int, float] | None = None,
) -> list[StatementLine]:
    lines: list[StatementLine] = []
    for y in years:
        fy = date(y, 12, 31)
        if y in total_assets:
            lines.append(
                StatementLine(
                    label="Total Assets",
                    concept="Assets",
                    fiscal_period_end=fy,
                    value=total_assets[y],
                    statement_type=StatementType.BALANCE,
                )
            )
        if y in total_liabilities:
            lines.append(
                StatementLine(
                    label="Total Liabilities",
                    concept="Liabilities",
                    fiscal_period_end=fy,
                    value=total_liabilities[y],
                    statement_type=StatementType.BALANCE,
                )
            )
        if equity and y in equity:
            lines.append(
                StatementLine(
                    label="Shareholders Equity",
                    concept="StockholdersEquity",
                    fiscal_period_end=fy,
                    value=equity[y],
                    statement_type=StatementType.BALANCE,
                )
            )
        if current_assets and y in current_assets:
            lines.append(
                StatementLine(
                    label="Current Assets",
                    concept="AssetsCurrent",
                    fiscal_period_end=fy,
                    value=current_assets[y],
                    statement_type=StatementType.BALANCE,
                )
            )
        if current_liabilities and y in current_liabilities:
            lines.append(
                StatementLine(
                    label="Current Liabilities",
                    concept="LiabilitiesCurrent",
                    fiscal_period_end=fy,
                    value=current_liabilities[y],
                    statement_type=StatementType.BALANCE,
                )
            )
    return lines
