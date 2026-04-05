from __future__ import annotations

import asyncio
import math

import yfinance as yf

from market_intel.domain.entities.financial_statement import StatementLine

from market_intel.application.dto.fundamentals_dto import (
    DcfScenarioDTO,
    DcfSensitivityDTO,
    FundamentalsDashboardDTO,
    StatementRowDTO,
)
from market_intel.domain.entities.financial_statement import StatementType
from market_intel.infrastructure.fundamentals.sec_company_facts_adapter import SecCompanyFactsFundamentalsAdapter
from market_intel.infrastructure.market_data.instrument_info import last_price_and_shares
from market_intel.modules.fundamentals.scores.altman_z import AltmanZInputs, altman_z_score
from market_intel.modules.fundamentals.scores.piotroski import (
    PiotroskiInput,
    PiotroskiYearSnapshot,
    piotroski_f_score,
)
from market_intel.modules.fundamentals.forensics import run_forensic_analysis
from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, discounted_cash_flow_value
from market_intel.modules.fundamentals.valuation.dcf_sensitivity import build_dcf_sensitivity_matrix
from market_intel.modules.fundamentals.valuation.roic import nopat_from_operating_income, roic_series
from market_intel.modules.fundamentals.valuation.wacc import WaccInputs, estimate_wacc
from market_intel.modules.fundamentals.xbrl.parse_facts import extract_tag_history


class FundamentalsService:
    def __init__(self, fundamentals: SecCompanyFactsFundamentalsAdapter) -> None:
        self._fundamentals = fundamentals

    def _rows_from_lines(self, lines: list[StatementLine]) -> list[StatementRowDTO]:
        out: list[StatementRowDTO] = []
        for ln in lines:
            fy = ln.fiscal_period_end.year
            out.append(StatementRowDTO(label=ln.label, fiscal_year=fy, value=ln.value))
        return out

    async def build_dashboard(self, symbol: str, years: int = 10) -> FundamentalsDashboardDTO:
        inc = await self._fundamentals.get_statement_series(symbol, StatementType.INCOME, years)
        bal = await self._fundamentals.get_statement_series(symbol, StatementType.BALANCE, years)
        cf = await self._fundamentals.get_statement_series(symbol, StatementType.CASHFLOW, years)

        facts = await self._fundamentals.get_company_facts(symbol)
        lt_debt_hist = self._year_map(
            extract_tag_history(facts, "us-gaap", "LongTermDebtNoncurrent")
        )
        if not lt_debt_hist:
            lt_debt_hist = self._year_map(extract_tag_history(facts, "us-gaap", "LongTermDebt"))
        shares_hist = self._year_map(
            extract_tag_history(
                facts,
                "us-gaap",
                "WeightedAverageNumberOfDilutedSharesOutstanding",
            )
        )
        if not shares_hist:
            shares_hist = self._year_map(
                extract_tag_history(facts, "us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic")
            )
        retained_hist = self._year_map(
            extract_tag_history(facts, "us-gaap", "RetainedEarningsAccumulatedDeficit")
        )
        ebit_hist = self._year_map(extract_tag_history(facts, "us-gaap", "OperatingIncomeLoss"))

        by_year: dict[int, dict[str, float]] = {}
        for ln in inc + bal + cf:
            y = ln.fiscal_period_end.year
            by_year.setdefault(y, {})[ln.label] = float(ln.value) if ln.value is not None else float("nan")

        years_sorted = sorted(by_year.keys(), reverse=True)
        latest_y = years_sorted[0] if years_sorted else None
        prior_y = years_sorted[1] if len(years_sorted) > 1 else None

        market_price, shares_out = await last_price_and_shares(symbol)

        def _get(y: int | None, *labels: str) -> float | None:
            if y is None:
                return None
            row = by_year.get(y, {})
            for lab in labels:
                v = row.get(lab)
                if v is not None and v == v:
                    return float(v)
            return None

        tax_rate = 0.21
        if latest_y is not None and prior_y is not None:
            cur = self._piotroski_snapshot(
                latest_y,
                by_year,
                lt_debt_hist,
                shares_hist,
                tax_rate,
            )
            prev = self._piotroski_snapshot(
                prior_y,
                by_year,
                lt_debt_hist,
                shares_hist,
                tax_rate,
            )
            p_score, p_flags = piotroski_f_score(PiotroskiInput(current=cur, prior=prev))
        else:
            p_score, p_flags = None, {}

        roic_val: float | None = None
        if latest_y is not None:
            oi = _get(latest_y, "Operating Income")
            if oi is None:
                oi = ebit_hist.get(latest_y)
            ni = _get(latest_y, "Net Income")
            assets = _get(latest_y, "Total Assets")
            equity = _get(latest_y, "Shareholders Equity")
            liab = _get(latest_y, "Total Liabilities")
            if oi is not None and assets is not None and equity is not None and liab is not None:
                nopat = nopat_from_operating_income(oi, tax_rate)
                invested = assets - (liab - (lt_debt_hist.get(latest_y, 0.0) or 0.0))
                rs = roic_series({latest_y: nopat}, {latest_y: invested})
                roic_val = rs.get(latest_y)

        beta = None

        def _yf_beta() -> float | None:
            t = yf.Ticker(symbol)
            b = (t.info or {}).get("beta")
            return float(b) if b is not None else None

        beta = await asyncio.to_thread(_yf_beta)

        mcap = None
        debt = None

        def _yf_cap_debt() -> tuple[float | None, float | None]:
            t = yf.Ticker(symbol)
            info = t.info or {}
            mc = info.get("marketCap")
            td = info.get("totalDebt")
            return (float(mc) if mc else None, float(td) if td else None)

        mcap, debt = await asyncio.to_thread(_yf_cap_debt)

        if latest_y is None:
            wacc = 0.09
            base_fcf = 0.0
        else:
            fcf = _get(latest_y, "Free Cash Flow (derived)")
            ocf = _get(latest_y, "Operating Cash Flow")
            capex = _get(latest_y, "Capital Expenditures")
            if fcf is None and ocf is not None and capex is not None:
                fcf = ocf - abs(capex)
            base_fcf = float(fcf or 0.0)
            cost_eq = 0.05 + (beta or 1.0) * 0.05
            pretax_debt = 0.05
            cost_debt_after = pretax_debt * (1.0 - tax_rate)
            e_val = mcap or 1.0
            d_val = debt or (lt_debt_hist.get(latest_y, 0.0) if latest_y else 0.0) or 0.0
            wacc = estimate_wacc(
                WaccInputs(
                    cost_of_equity=cost_eq,
                    cost_of_debt_after_tax=cost_debt_after,
                    equity_market_value=max(e_val, 1.0),
                    debt_book_value=max(d_val, 0.0),
                    tax_rate=tax_rate,
                )
            )

        dcf_res = discounted_cash_flow_value(
            DcfInputs(
                base_free_cash_flow=max(base_fcf, 1.0),
                growth_years_1_to_5=0.05,
                terminal_growth=0.02,
                wacc=max(wacc, 0.04),
            ),
            shares_outstanding=shares_out,
            net_debt=(debt or 0.0) - 0.0,
        )

        altman: float | None = None
        if latest_y is not None:
            ca = _get(latest_y, "Current Assets") or 0.0
            cl = _get(latest_y, "Current Liabilities") or 0.0
            ta = _get(latest_y, "Total Assets") or 0.0
            tl = _get(latest_y, "Total Liabilities") or 0.0
            sales = _get(latest_y, "Revenue") or 0.0
            re = retained_hist.get(latest_y, 0.0) or 0.0
            ebit = ebit_hist.get(latest_y, _get(latest_y, "Operating Income")) or 0.0
            mve = mcap or (market_price or 0.0) * (shares_out or 0.0)
            if ta > 0 and tl > 0 and mve > 0:
                altman = altman_z_score(
                    AltmanZInputs(
                        working_capital=ca - cl,
                        total_assets=ta,
                        retained_earnings=re,
                        ebit=ebit,
                        market_value_equity=mve,
                        total_liabilities=tl,
                        sales=sales,
                    )
                )

        mos: float | None = None
        if market_price and dcf_res.implied_per_share:
            mos = (dcf_res.implied_per_share - market_price) / market_price * 100.0

        forensic_flags = run_forensic_analysis(facts, by_year, latest_y, prior_y)

        net_debt_val = float(debt or 0.0)
        w_eff = max(float(wacc), 0.04)
        w_axis, t_axis, sens_mat = build_dcf_sensitivity_matrix(
            base_free_cash_flow=max(base_fcf, 1.0),
            shares_outstanding=shares_out,
            net_debt=net_debt_val,
            growth_years_1_to_5=0.05,
            base_wacc=w_eff,
            base_terminal_growth=0.02,
            wacc_half_span=0.02,
            terminal_half_span=0.01,
            grid_size=5,
        )
        dcf_sensitivity = DcfSensitivityDTO(
            wacc_values=w_axis,
            terminal_growth_values=t_axis,
            intrinsic_per_share_matrix=sens_mat,
            base_growth_high=0.05,
            net_debt=net_debt_val,
        )

        return FundamentalsDashboardDTO(
            symbol=symbol.upper(),
            income=self._rows_from_lines(inc),
            balance=self._rows_from_lines(bal),
            cashflow=self._rows_from_lines(cf),
            wacc=float(wacc),
            dcf_base=DcfScenarioDTO(
                growth_high=0.05,
                terminal_growth=0.02,
                wacc=float(wacc),
                intrinsic_per_share=dcf_res.implied_per_share,
                enterprise_value=dcf_res.enterprise_value,
            ),
            roic_latest=roic_val,
            piotroski_score=p_score,
            piotroski_flags=p_flags,
            altman_z=float(altman) if altman is not None and math.isfinite(altman) else None,
            market_price=market_price,
            margin_of_safety_pct=mos,
            forensic_flags=forensic_flags,
            dcf_sensitivity=dcf_sensitivity,
        )

    def _year_map(self, hist: list[tuple[str, float]]) -> dict[int, float]:
        m: dict[int, float] = {}
        for end, val in hist:
            y = int(end[:4])
            m[y] = val
        return m

    def _piotroski_snapshot(
        self,
        year: int,
        by_year: dict[int, dict[str, float]],
        lt_debt: dict[int, float],
        shares: dict[int, float],
        tax_rate: float,
    ) -> PiotroskiYearSnapshot:
        row = by_year.get(year, {})
        ni = float(row.get("Net Income", float("nan")))
        ocf = float(row.get("Operating Cash Flow", float("nan")))
        assets = float(row.get("Total Assets", float("nan")))
        rev = float(row.get("Revenue", float("nan")))
        gp = float(row.get("Gross Profit", float("nan")))
        ca = float(row.get("Current Assets", float("nan")))
        cl = float(row.get("Current Liabilities", float("nan")))
        sh = float(shares.get(year, float("nan")))
        ltd = float(lt_debt.get(year, float("nan")))
        roa = ni / assets if assets and assets == assets else 0.0
        cr = ca / cl if cl and cl == cl and cl != 0 else 0.0
        gm = gp / rev if rev and rev == rev and rev != 0 else 0.0
        at = rev / assets if assets and assets == assets and assets != 0 else 0.0
        return PiotroskiYearSnapshot(
            net_income=ni,
            operating_cash_flow=ocf,
            roa=roa,
            long_term_debt=ltd if ltd == ltd else 0.0,
            current_ratio=cr,
            shares_outstanding=sh if sh == sh else 0.0,
            gross_margin=gm,
            asset_turnover=at,
        )
