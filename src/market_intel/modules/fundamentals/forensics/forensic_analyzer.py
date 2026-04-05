"""
Forensic accounting-style flags on fundamentals payload + SEC facts.
Educational heuristics — not an audit opinion.
"""

from __future__ import annotations

import math
from typing import Any

from market_intel.application.dto.fundamentals_dto import ForensicFlagDTO
from market_intel.modules.fundamentals.xbrl.parse_facts import extract_tag_history


def _year_map_from_hist(hist: list[tuple[str, float]]) -> dict[int, float]:
    """Keep latest fiscal end per calendar year."""
    by_year: dict[int, list[tuple[str, float]]] = {}
    for end, val in hist:
        if not end or val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        y = int(str(end)[:4])
        by_year.setdefault(y, []).append((str(end), float(val)))
    out: dict[int, float] = {}
    for y, pairs in by_year.items():
        _, v = max(pairs, key=lambda x: x[0])
        out[y] = v
    return out


def _get_year(by_year: dict[int, dict[str, float]], y: int | None, *labels: str) -> float | None:
    if y is None:
        return None
    row = by_year.get(y, {})
    for lab in labels:
        v = row.get(lab)
        if v is not None and v == v:
            return float(v)
    return None


def _first_tag_map(
    facts: dict[str, Any],
    taxonomy: str,
    candidates: tuple[str, ...],
) -> dict[int, float]:
    for tag in candidates:
        hist = extract_tag_history(facts, taxonomy, tag)
        m = _year_map_from_hist(hist)
        if m:
            return m
    return {}


def _dso_days(receivables: float, revenue: float) -> float | None:
    if revenue is None or receivables is None or revenue <= 0 or receivables < 0:
        return None
    return (receivables / revenue) * 365.0


def _beneish_m_score(
    t: int,
    t1: int,
    sales: dict[int, float],
    rec: dict[int, float],
    cogs: dict[int, float],
    ca: dict[int, float],
    ppe: dict[int, float],
    ta: dict[int, float],
    dep: dict[int, float],
    sga: dict[int, float],
    ni: dict[int, float],
    ocf: dict[int, float],
    ltd: dict[int, float],
    cl: dict[int, float],
) -> tuple[float | None, str | None]:
    """Beneish M-Score approximation from annual maps. Returns (m, error)."""

    def gv(d: dict[int, float], y: int) -> float | None:
        v = d.get(y)
        return v if v is not None and v == v else None

    s_t, s_t1 = gv(sales, t), gv(sales, t1)
    r_t, r_t1 = gv(rec, t), gv(rec, t1)
    if not all([s_t, s_t1, r_t, r_t1]) or s_t <= 0 or s_t1 <= 0:
        return None, "חסרים נתוני מכירות/חובות לקוחות לשנים השוואתיות"

    dsri_num = (r_t / s_t) / max((r_t1 / s_t1), 1e-9)

    cg_t = gv(cogs, t)
    cg_t1 = gv(cogs, t1)
    if cg_t is None or cg_t1 is None:
        return None, "חסר Cost of Revenue ל־Beneish"
    gmi_t = (s_t - cg_t) / s_t
    gmi_t1 = (s_t1 - cg_t1) / s_t1
    gmi = (gmi_t1 / max(gmi_t, 1e-9)) if gmi_t > 0 else 1.0

    ca_t, ca_t1 = gv(ca, t), gv(ca, t1)
    ppe_t, ppe_t1 = gv(ppe, t), gv(ppe, t1)
    ta_t, ta_t1 = gv(ta, t), gv(ta, t1)
    if None in (ca_t, ca_t1, ppe_t, ppe_t1, ta_t, ta_t1) or ta_t <= 0 or ta_t1 <= 0:
        return None, "חסרים נתוני מאזן (נכסים/סעיפים) ל־AQI"

    aqi = (1.0 - (ca_t + ppe_t) / ta_t) / max(1e-9, (1.0 - (ca_t1 + ppe_t1) / ta_t1))

    sgi = s_t / max(s_t1, 1e-9)

    dep_t, dep_t1 = gv(dep, t), gv(dep, t1)
    if dep_t is None or dep_t1 is None:
        return None, "חסר פחת ל־DEPI"
    ppe_denom_t = ppe_t + dep_t
    ppe_denom_t1 = ppe_t1 + dep_t1
    if ppe_denom_t <= 0 or ppe_denom_t1 <= 0:
        return None, "פחת/PPE לא תקינים"
    depi = (dep_t1 / ppe_denom_t1) / max(dep_t / ppe_denom_t, 1e-9)

    sga_t, sga_t1 = gv(sga, t), gv(sga, t1)
    if sga_t is None or sga_t1 is None:
        return None, "חסר SGA ל־SGAI"
    sgai = (sga_t / s_t) / max(sga_t1 / s_t1, 1e-9)

    ni_t, ocf_t = gv(ni, t), gv(ocf, t)
    if ni_t is None or ocf_t is None or ta_t <= 0:
        return None, "חסר רווח נקי או תזרים תפעולי ל־TATA"
    tata = (ni_t - ocf_t) / ta_t

    ltd_t, ltd_t1 = gv(ltd, t), gv(ltd, t1)
    cl_t, cl_t1 = gv(cl, t), gv(cl, t1)
    if None in (ltd_t, ltd_t1, cl_t, cl_t1) or ta_t <= 0 or ta_t1 <= 0:
        return None, "חסרים חוב ל־LVGI"
    lev_t = (ltd_t + cl_t) / ta_t
    lev_t1 = (ltd_t1 + cl_t1) / ta_t1
    lvgi = lev_t / max(lev_t1, 1e-9)

    m = (
        -4.84
        + 0.92 * dsri_num
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    return float(m), None


def run_forensic_analysis(
    facts: dict[str, Any],
    by_year: dict[int, dict[str, float]],
    latest_y: int | None,
    prior_y: int | None,
) -> list[ForensicFlagDTO]:
    flags: list[ForensicFlagDTO] = []

    if latest_y is None or prior_y is None:
        return [
            ForensicFlagDTO(
                severity="info",
                code="insufficient_history",
                title_he="חסרה היסטוריה שנתית כפולה",
                detail_he="הבדיקות הפורנזיות דורשות לפחות שתי שנות דוח זמינות.",
            )
        ]

    ni_l = _get_year(by_year, latest_y, "Net Income")
    ni_p = _get_year(by_year, prior_y, "Net Income")
    ocf_l = _get_year(by_year, latest_y, "Operating Cash Flow")
    ocf_p = _get_year(by_year, prior_y, "Operating Cash Flow")
    if all(v is not None for v in (ni_l, ni_p, ocf_l, ocf_p)):
        ni_up = ni_l > ni_p * 1.03
        ocf_down = ocf_l < ocf_p * 0.97
        if ni_up and ocf_down:
            flags.append(
                ForensicFlagDTO(
                    severity="high",
                    code="earnings_quality_cfo",
                    title_he="איכות רווח — דגל אדום",
                    detail_he=(
                        f"הרווח הנקי עלה מ־{ni_p:,.0f} ל־{ni_l:,.0f} (שנה {prior_y}→{latest_y}), "
                        f"אבל תזרים מפעילות שוטפת **ירד** מ־{ocf_p:,.0f} ל־{ocf_l:,.0f}. "
                        "בפורנזיקה חשבונאית זה לעיתים סימן שרווחים \"איכותיים\" פחות או שינויים בתזמון מזומנים — "
                        "לא הוכחה להונאה; דורש בדיקת accruals והערות בדוח."
                    ),
                )
            )

    rec = _first_tag_map(
        facts,
        "us-gaap",
        (
            "AccountsReceivableNetCurrent",
            "AccountsReceivableNet",
            "TradeAndOtherReceivablesNetCurrent",
        ),
    )
    sales_map = _first_tag_map(facts, "us-gaap", ("Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"))

    if sales_map:
        rev_l = _get_year(by_year, latest_y, "Revenue") or sales_map.get(latest_y)
        rev_p = _get_year(by_year, prior_y, "Revenue") or sales_map.get(prior_y)
        ar_l = rec.get(latest_y)
        ar_p = rec.get(prior_y)
        if rev_l and rev_p and ar_l is not None and ar_p is not None and rev_l > 0 and rev_p > 0:
            dso_l = _dso_days(ar_l, rev_l)
            dso_p = _dso_days(ar_p, rev_p)
            if dso_l is not None and dso_p is not None and dso_p > 1:
                change = (dso_l - dso_p) / dso_p
                if change > 0.12:
                    flags.append(
                        ForensicFlagDTO(
                            severity="medium",
                            code="dso_stretch",
                            title_he="Days Sales Outstanding (DSO) — התארכות גבייה",
                            detail_he=(
                                f"מוערך ימי מכירה מוצגים (Receivables/Revenue×365): "
                                f"~{dso_l:.0f} ימים ב־{latest_y} לעומת ~{dso_p:.0f} ב־{prior_y} "
                                f"(שינוי של כ־{change * 100:.0f}%). "
                                "התארכות גבייה יכולה להעיד על לחץ על לקוחות, הכרה מוקדמת של הכנסות, או שינוי תנאי אשראי — "
                                "כדאי להשוות לתעשייה ולדוח המלא."
                            ),
                        )
                    )

    sales = sales_map or {}
    if not sales:
        for y in (latest_y, prior_y):
            r = _get_year(by_year, y, "Revenue")
            if r is not None:
                sales[y] = r
    cogs = _first_tag_map(
        facts,
        "us-gaap",
        ("CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"),
    )
    ca = _first_tag_map(facts, "us-gaap", ("AssetsCurrent",))
    ppe = _first_tag_map(facts, "us-gaap", ("PropertyPlantAndEquipmentNet",))
    ta = _first_tag_map(facts, "us-gaap", ("Assets",))
    dep = _first_tag_map(
        facts,
        "us-gaap",
        (
            "DepreciationAndAmortization",
            "DepreciationDepletionAndAmortization",
            "Depreciation",
        ),
    )
    sga = _first_tag_map(
        facts,
        "us-gaap",
        ("SellingGeneralAndAdministrativeExpense", "SellingAndMarketingExpense"),
    )
    ni_map = _first_tag_map(facts, "us-gaap", ("NetIncomeLoss",))
    ocf_map = _first_tag_map(
        facts,
        "us-gaap",
        ("NetCashProvidedByUsedInOperatingActivities",),
    )
    ltd = _first_tag_map(
        facts,
        "us-gaap",
        ("LongTermDebtNoncurrent", "LongTermDebt"),
    )
    cl_map = _first_tag_map(facts, "us-gaap", ("LiabilitiesCurrent",))

    for yk, lab in ((latest_y, "Net Income"), (prior_y, "Net Income")):
        v = _get_year(by_year, yk, lab)
        if v is not None and yk not in ni_map:
            ni_map[yk] = v
    for yk in (latest_y, prior_y):
        v = _get_year(by_year, yk, "Operating Cash Flow")
        if v is not None and yk not in ocf_map:
            ocf_map[yk] = v

    if not rec:
        m_score, err = None, "אין מפת חובות לקוחות מספיקת ל־Beneish"
    else:
        m_score, err = _beneish_m_score(
            latest_y,
            prior_y,
            sales,
            rec,
            cogs,
            ca,
            ppe,
            ta,
            dep,
            sga,
            ni_map,
            ocf_map,
            ltd,
            cl_map,
        )
    if m_score is not None:
        manipulator_zone = m_score > -1.78
        flags.append(
            ForensicFlagDTO(
                severity="high" if manipulator_zone else "info",
                code="beneish_m",
                title_he=f"Beneish M-Score ≈ {m_score:.3f}",
                detail_he=(
                    "מדד סטטיסטי לזיהוי **הסתברות** למניפולציה ברווחים (מודל Beneish; מבוסס דיווחים שנתיים). "
                    f"ערך מעל **‎-1.78** נחשב לרוב לאזור **סיכון מוגבר** בהתפלגות המקורית — לא אבחנה ולא הוכחה. "
                    "ערך נמוך מ־‎-1.78 נחשב לרוב \"צפוי\" יותר."
                ),
            )
        )
    elif err:
        flags.append(
            ForensicFlagDTO(
                severity="info",
                code="beneish_skip",
                title_he="Beneish M-Score — לא חושב",
                detail_he=f"לא ניתן להשלים את כל רכיבי הנוסחה: {err}",
            )
        )

    if not flags:
        flags.append(
            ForensicFlagDTO(
                severity="info",
                code="no_major_flags",
                title_he="לא זוהו דגלים חזקים מהבדיקות האוטומטיות",
                detail_he=(
                    "המערכת לא מצאה את התבניות שסימנו (רווח מול CFO, DSO, או Beneish חריג). "
                    "זה לא אומר שהדוח \"נקי\" — רק שההיוריסטיקות לא התריעו."
                ),
            )
        )

    return flags
