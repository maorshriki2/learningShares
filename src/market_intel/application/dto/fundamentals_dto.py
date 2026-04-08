from pydantic import BaseModel, Field


class StatementRowDTO(BaseModel):
    label: str
    fiscal_year: int
    value: float | None


class DcfScenarioDTO(BaseModel):
    growth_high: float
    terminal_growth: float
    wacc: float
    intrinsic_per_share: float | None
    enterprise_value: float


class ForensicFlagDTO(BaseModel):
    severity: str
    code: str
    title_he: str
    detail_he: str
    explain: dict[str, object] = Field(default_factory=dict)


class DcfSensitivityDTO(BaseModel):
    """WACC rows × terminal growth columns → intrinsic per share."""

    wacc_values: list[float]
    terminal_growth_values: list[float]
    intrinsic_per_share_matrix: list[list[float | None]]
    base_growth_high: float
    net_debt: float


class WaccExplainDTO(BaseModel):
    beta: float | None = None
    beta_source: str | None = None
    tax_rate: float | None = None
    cost_of_equity: float | None = None
    cost_of_equity_assumptions: dict[str, float] = Field(default_factory=dict)
    pretax_cost_of_debt: float | None = None
    cost_of_debt_after_tax: float | None = None
    equity_market_value: float | None = None
    debt_value: float | None = None
    total_value: float | None = None
    weight_equity: float | None = None
    weight_debt: float | None = None
    wacc: float | None = None
    notes: list[str] = Field(default_factory=list)


class DcfProjectionYearDTO(BaseModel):
    year_index: int
    free_cash_flow: float
    discount_factor: float
    present_value: float


class DcfExplainDTO(BaseModel):
    base_free_cash_flow: float | None = None
    base_fcf_source: str | None = None
    growth_years_1_to_5: float | None = None
    terminal_growth_input: float | None = None
    terminal_growth_effective: float | None = None
    wacc: float | None = None
    projection_years: int | None = None
    projections: list[DcfProjectionYearDTO] = Field(default_factory=list)
    pv_explicit: float | None = None
    terminal_value: float | None = None
    pv_terminal: float | None = None
    enterprise_value: float | None = None
    net_debt: float | None = None
    equity_value: float | None = None
    shares_outstanding: float | None = None
    implied_per_share: float | None = None
    notes: list[str] = Field(default_factory=list)


class FundamentalsDashboardDTO(BaseModel):
    symbol: str
    income: list[StatementRowDTO]
    balance: list[StatementRowDTO]
    cashflow: list[StatementRowDTO]
    wacc: float
    dcf_base: DcfScenarioDTO
    roic_latest: float | None
    piotroski_score: int | None
    piotroski_flags: dict[str, int] = Field(default_factory=dict)
    altman_z: float | None
    market_price: float | None
    margin_of_safety_pct: float | None
    forensic_flags: list[ForensicFlagDTO] = Field(default_factory=list)
    dcf_sensitivity: DcfSensitivityDTO | None = None
    wacc_explain: WaccExplainDTO | None = None
    dcf_explain: DcfExplainDTO | None = None
    # Latest fiscal year KPI snapshot (USD, SEC-derived) for UI row
    kpi_fiscal_year: int | None = None
    revenue_latest_usd: float | None = None
    gross_profit_latest_usd: float | None = None
    operating_income_latest_usd: float | None = None
    ebitda_latest_usd: float | None = None
    net_income_latest_usd: float | None = None
