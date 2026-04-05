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


class DcfSensitivityDTO(BaseModel):
    """WACC rows × terminal growth columns → intrinsic per share."""

    wacc_values: list[float]
    terminal_growth_values: list[float]
    intrinsic_per_share_matrix: list[list[float | None]]
    base_growth_high: float
    net_debt: float


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
