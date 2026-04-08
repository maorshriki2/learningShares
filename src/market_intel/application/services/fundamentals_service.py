from __future__ import annotations

import asyncio
import math

import yfinance as yf

from market_intel.application.dto.fundamentals_dto import (
    DcfScenarioDTO,
    DcfExplainDTO,
    DcfProjectionYearDTO,
    DcfSensitivityDTO,
    FundamentalsDashboardDTO,
    StatementRowDTO,
    WaccExplainDTO,
)
from market_intel.domain.entities.financial_statement import StatementLine, StatementType
from market_intel.infrastructure.fundamentals.sec_company_facts_adapter import (
    SecCompanyFactsFundamentalsAdapter,
)
from market_intel.infrastructure.market_data.instrument_info import last_price_and_shares
from market_intel.modules.fundamentals.forensics import run_forensic_analysis
from market_intel.modules.fundamentals.scores.altman_z import AltmanZInputs, altman_z_score
from market_intel.modules.fundamentals.scores.piotroski import (
    PiotroskiInput,
    PiotroskiYearSnapshot,
    piotroski_f_score,
)
from market_intel.modules.fundamentals.valuation.dcf import DcfInputs, discounted_cash_flow_value
from market_intel.modules.fundamentals.valuation.dcf_sensitivity import build_dcf_sensitivity_matrix
from market_intel.modules.fundamentals.valuation.roic import (
    nopat_from_operating_income,
    roic_series,
)
from market_intel.modules.fundamentals.valuation.wacc import WaccInputs, estimate_wacc
from market_intel.modules.fundamentals.xbrl.normalize_statements import (
    OPERATING_INCOME_FALLBACK_TAGS,
    annual_series_preferred_tags_per_year,
)
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
                extract_tag_history(
                    facts,
                    "us-gaap",
                    "WeightedAverageNumberOfSharesOutstandingBasic",
                )
            )
        retained_hist = self._year_map(
            extract_tag_history(facts, "us-gaap", "RetainedEarningsAccumulatedDeficit")
        )
        ebit_hist = annual_series_preferred_tags_per_year(
            facts, "us-gaap", OPERATING_INCOME_FALLBACK_TAGS
        )

        by_year: dict[int, dict[str, float]] = {}
        for ln in inc + bal + cf:
            y = ln.fiscal_period_end.year
            val = float(ln.value) if ln.value is not None else float("nan")
            by_year.setdefault(y, {})[ln.label] = val

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
            base_fcf_source = "missing_latest_year"
            cost_eq = None
            pretax_debt = None
            cost_debt_after = None
            e_val = None
            d_val = None
        else:
            fcf = _get(latest_y, "Free Cash Flow (derived)")
            ocf = _get(latest_y, "Operating Cash Flow")
            capex = _get(latest_y, "Capital Expenditures")
            base_fcf_source = "Free Cash Flow (derived)"
            if fcf is None and ocf is not None and capex is not None:
                fcf = ocf - abs(capex)
                base_fcf_source = "Operating Cash Flow - |CapEx|"
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

        # --- Explain payloads (transparent intermediates for UI) ---
        wacc_notes: list[str] = []
        if latest_y is None:
            wacc_notes.append("No fiscal-year snapshot → using default WACC (0.09).")
        if beta is None:
            wacc_notes.append("Beta missing → defaulted to 1.0 in cost of equity heuristic.")
        if mcap is None:
            wacc_notes.append("Market cap missing → defaulted equity value (E) to 1.0 for weights.")
        if debt is None and latest_y is not None:
            wacc_notes.append(
                "Total debt missing in yfinance → using LongTermDebt history fallback (book)."
            )

        e_used = float(max(e_val, 1.0)) if e_val is not None else None
        d_used = float(max(d_val, 0.0)) if d_val is not None else None
        v_used = float((e_used or 0.0) + (d_used or 0.0)) if (e_used is not None and d_used is not None) else None
        w_e = (e_used / v_used) if (v_used is not None and v_used > 0 and e_used is not None) else None
        w_d = (d_used / v_used) if (v_used is not None and v_used > 0 and d_used is not None) else None

        wacc_explain = WaccExplainDTO(
            beta=float(beta) if beta is not None else None,
            beta_source="yfinance.info.beta",
            tax_rate=float(tax_rate),
            cost_of_equity=float(cost_eq) if cost_eq is not None else None,
            cost_of_equity_assumptions={"rf": 0.05, "erp": 0.05},
            pretax_cost_of_debt=float(pretax_debt) if pretax_debt is not None else None,
            cost_of_debt_after_tax=float(cost_debt_after) if cost_debt_after is not None else None,
            equity_market_value=float(e_used) if e_used is not None else None,
            debt_value=float(d_used) if d_used is not None else None,
            total_value=float(v_used) if v_used is not None else None,
            weight_equity=float(w_e) if w_e is not None else None,
            weight_debt=float(w_d) if w_d is not None else None,
            wacc=float(wacc) if wacc is not None else None,
            notes=wacc_notes,
        )

        # DCF explain (match dcf.py logic exactly, including terminal growth clamp)
        dcf_inputs = DcfInputs(
            base_free_cash_flow=max(base_fcf, 1.0),
            growth_years_1_to_5=0.05,
            terminal_growth=0.02,
            wacc=max(wacc, 0.04),
        )
        wacc_eff = max(float(dcf_inputs.wacc), 0.0005)
        gt_eff = min(float(dcf_inputs.terminal_growth), wacc_eff - 0.0005)
        fcf_walk = float(dcf_inputs.base_free_cash_flow)
        projections: list[DcfProjectionYearDTO] = []
        pv_exp = 0.0
        for t in range(1, int(dcf_inputs.projection_years) + 1):
            fcf_walk *= 1.0 + float(dcf_inputs.growth_years_1_to_5)
            dfac = 1.0 / ((1.0 + wacc_eff) ** t)
            pv_t = fcf_walk * dfac
            pv_exp += pv_t
            projections.append(
                DcfProjectionYearDTO(
                    year_index=t,
                    free_cash_flow=float(fcf_walk),
                    discount_factor=float(dfac),
                    present_value=float(pv_t),
                )
            )
        tv = fcf_walk * (1.0 + gt_eff) / (wacc_eff - gt_eff)
        pv_tv = tv / ((1.0 + wacc_eff) ** int(dcf_inputs.projection_years))
        ev = pv_exp + pv_tv
        net_debt_used = float((debt or 0.0) - 0.0)
        eqv = ev - net_debt_used
        per_share = (
            (eqv / float(shares_out)) if shares_out is not None and float(shares_out) > 0 else None
        )
        dcf_notes: list[str] = []
        if base_fcf_source != "Free Cash Flow (derived)":
            dcf_notes.append(f"Base FCF derived via: {base_fcf_source}.")
        if float(dcf_inputs.terminal_growth) != float(gt_eff):
            dcf_notes.append(
                "Terminal growth was clamped to remain below WACC (gt = min(input, wacc-0.0005))."
            )
        if shares_out is None:
            dcf_notes.append("Shares outstanding missing → implied per share is not computed.")

        dcf_explain = DcfExplainDTO(
            base_free_cash_flow=float(max(base_fcf, 1.0)) if base_fcf is not None else None,
            base_fcf_source=str(base_fcf_source),
            growth_years_1_to_5=float(dcf_inputs.growth_years_1_to_5),
            terminal_growth_input=float(dcf_inputs.terminal_growth),
            terminal_growth_effective=float(gt_eff),
            wacc=float(wacc_eff),
            projection_years=int(dcf_inputs.projection_years),
            projections=projections,
            pv_explicit=float(pv_exp),
            terminal_value=float(tv),
            pv_terminal=float(pv_tv),
            enterprise_value=float(ev),
            net_debt=float(net_debt_used),
            equity_value=float(eqv),
            shares_outstanding=float(shares_out) if shares_out is not None else None,
            implied_per_share=float(per_share) if per_share is not None else None,
            notes=dcf_notes,
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

        def _kpi_float(y: int | None, *labels: str) -> float | None:
            v = _get(y, *labels)
            return float(v) if v is not None and math.isfinite(v) else None

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
            wacc_explain=wacc_explain,
            dcf_explain=dcf_explain,
            kpi_fiscal_year=latest_y,
            revenue_latest_usd=_kpi_float(latest_y, "Revenue"),
            gross_profit_latest_usd=_kpi_float(latest_y, "Gross Profit"),
            operating_income_latest_usd=_kpi_float(latest_y, "Operating Income"),
            ebitda_latest_usd=_kpi_float(latest_y, "EBITDA"),
            net_income_latest_usd=_kpi_float(latest_y, "Net Income"),
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
