"""
Forensic accounting-style flags on fundamentals payload + SEC facts.
Educational heuristics — not an audit opinion.
"""

from __future__ import annotations

import math
from typing import Any

from market_intel.application.dto.fundamentals_dto import ForensicFlagDTO
from market_intel.modules.fundamentals.xbrl.parse_facts import extract_tag_history
from market_intel.ui.formatters.bidi_text import md_code as _md


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
    total_liab: dict[int, float],
) -> tuple[float | None, str | None, str | None, dict[str, object]]:
    """Beneish M-Score approximation from annual maps. Returns (m, error, lvgi_note, explain)."""

    def gv(d: dict[int, float], y: int) -> float | None:
        v = d.get(y)
        return v if v is not None and v == v else None

    s_t, s_t1 = gv(sales, t), gv(sales, t1)
    r_t, r_t1 = gv(rec, t), gv(rec, t1)
    if not all([s_t, s_t1, r_t, r_t1]) or s_t <= 0 or s_t1 <= 0:
        return None, "חסרים נתוני מכירות/חובות לקוחות לשנים השוואתיות", None, {}

    dsri_num = (r_t / s_t) / max((r_t1 / s_t1), 1e-9)

    cg_t = gv(cogs, t)
    cg_t1 = gv(cogs, t1)
    if cg_t is None or cg_t1 is None:
        return None, "חסר Cost of Revenue ל־Beneish", None, {}
    gmi_t = (s_t - cg_t) / s_t
    gmi_t1 = (s_t1 - cg_t1) / s_t1
    gmi = (gmi_t1 / max(gmi_t, 1e-9)) if gmi_t > 0 else 1.0

    ca_t, ca_t1 = gv(ca, t), gv(ca, t1)
    ppe_t, ppe_t1 = gv(ppe, t), gv(ppe, t1)
    ta_t, ta_t1 = gv(ta, t), gv(ta, t1)
    if None in (ca_t, ca_t1, ppe_t, ppe_t1, ta_t, ta_t1) or ta_t <= 0 or ta_t1 <= 0:
        return None, "חסרים נתוני מאזן (נכסים/סעיפים) ל־AQI", None, {}

    aqi = (1.0 - (ca_t + ppe_t) / ta_t) / max(1e-9, (1.0 - (ca_t1 + ppe_t1) / ta_t1))

    sgi = s_t / max(s_t1, 1e-9)

    dep_t, dep_t1 = gv(dep, t), gv(dep, t1)
    if dep_t is None or dep_t1 is None:
        return None, "חסר פחת ל־DEPI", None, {}
    ppe_denom_t = ppe_t + dep_t
    ppe_denom_t1 = ppe_t1 + dep_t1
    if ppe_denom_t <= 0 or ppe_denom_t1 <= 0:
        return None, "פחת/PPE לא תקינים", None, {}
    depi = (dep_t1 / ppe_denom_t1) / max(dep_t / ppe_denom_t, 1e-9)

    sga_t, sga_t1 = gv(sga, t), gv(sga, t1)
    if sga_t is None or sga_t1 is None:
        return None, "חסר SGA ל־SGAI", None, {}
    sgai = (sga_t / s_t) / max(sga_t1 / s_t1, 1e-9)

    ni_t, ocf_t = gv(ni, t), gv(ocf, t)
    if ni_t is None or ocf_t is None or ta_t <= 0:
        return None, "חסר רווח נקי או תזרים תפעולי ל־TATA", None, {}
    tata = (ni_t - ocf_t) / ta_t

    ltd_t, ltd_t1 = gv(ltd, t), gv(ltd, t1)
    cl_t, cl_t1 = gv(cl, t), gv(cl, t1)
    tl_t, tl_t1 = gv(total_liab, t), gv(total_liab, t1)

    lvgi_note: str | None = None

    if None not in (ltd_t, ltd_t1, cl_t, cl_t1):
        lev_t = (ltd_t + cl_t) / ta_t
        lev_t1 = (ltd_t1 + cl_t1) / ta_t1
        lvgi = lev_t / max(lev_t1, 1e-9)
    elif None not in (tl_t, tl_t1):
        # Many filers omit standalone LongTermDebt; TL/TA YoY captures leverage similarly.
        lev_t = tl_t / ta_t
        lev_t1 = tl_t1 / ta_t1
        lvgi = lev_t / max(lev_t1, 1e-9)
        lvgi_note = (
            f"- {_md('LVGI')}: מחושב מ־{_md('Total Liabilities / Total Assets')} "
            f"כי {_md('long-term debt')} לא זמין ב־{_md('XBRL')}."
        )
    else:
        return (
            None,
            "חסרים נתוני התחייבויות ל־LVGI (חוב ארוך+שוטף או סה״כ התחייבויות).",
            None,
            {},
        )

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

    explain: dict[str, object] = {
        "years": {"t": t, "t1": t1},
        "components": {
            "DSRI": float(dsri_num),
            "GMI": float(gmi),
            "AQI": float(aqi),
            "SGI": float(sgi),
            "DEPI": float(depi),
            "SGAI": float(sgai),
            "TATA": float(tata),
            "LVGI": float(lvgi),
        },
        "raw_inputs": {
            "sales_t": float(s_t),
            "sales_t1": float(s_t1),
            "receivables_t": float(r_t),
            "receivables_t1": float(r_t1),
            "cogs_t": float(cg_t),
            "cogs_t1": float(cg_t1),
            "current_assets_t": float(ca_t),
            "current_assets_t1": float(ca_t1),
            "ppe_t": float(ppe_t),
            "ppe_t1": float(ppe_t1),
            "total_assets_t": float(ta_t),
            "total_assets_t1": float(ta_t1),
            "depreciation_t": float(dep_t),
            "depreciation_t1": float(dep_t1),
            "sga_t": float(sga_t),
            "sga_t1": float(sga_t1),
            "net_income_t": float(ni_t),
            "ocf_t": float(ocf_t),
            "ltd_t": float(ltd_t) if ltd_t is not None else None,
            "ltd_t1": float(ltd_t1) if ltd_t1 is not None else None,
            "current_liabilities_t": float(cl_t) if cl_t is not None else None,
            "current_liabilities_t1": float(cl_t1) if cl_t1 is not None else None,
            "total_liabilities_t": float(tl_t) if tl_t is not None else None,
            "total_liabilities_t1": float(tl_t1) if tl_t1 is not None else None,
        },
        "thresholds": {"manipulator_zone_if_gt": -1.78},
        "lvgi_note": lvgi_note,
    }

    return float(m), None, lvgi_note, explain


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
                detail_he=(
                    "- נדרשות לפחות " + _md(2) + " שנות דוח זמינות.\n"
                    "- בלי זה אין השוואה שנתית אמינה."
                ),
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
                        "**איכות רווח — אי־התאמה**\n\n"
                        "**נתונים מהדוח:**\n"
                        f"- {_md('Net Income')}: {_md(f'{ni_p:,.0f}')} → {_md(f'{ni_l:,.0f}')} "
                        f"(שנות דוח {_md(prior_y)} → {_md(latest_y)}).\n"
                        f"- {_md('Operating cash flow')}: {_md(f'{ocf_p:,.0f}')} → {_md(f'{ocf_l:,.0f}')} "
                        "(**ירידה**).\n\n"
                        "**פירוש קצר:**\n"
                        "- רווח עולה כשהתזרים התפעולי יורד — לבדוק accruals והערות בדוח.\n"
                        "- זה **לא** הוכחה להונאה."
                    ),
                    explain={
                        "latest_year": latest_y,
                        "prior_year": prior_y,
                        "net_income_latest": float(ni_l),
                        "net_income_prior": float(ni_p),
                        "ocf_latest": float(ocf_l),
                        "ocf_prior": float(ocf_p),
                        "thresholds": {
                            "ni_up_factor": 1.03,
                            "ocf_down_factor": 0.97,
                        },
                        "triggered": {"ni_up": True, "ocf_down": True},
                    },
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
                            title_he=f"התארכות גבייה — {_md('DSO')}",
                            detail_he=(
                                f"**מה זה {_md('DSO')}?**\n"
                                "- ימים משוערים עד גביית מכירות.\n"
                                f"- השנים הן {_md('fiscal year')} מהדוח — לא בהכרח היום בלוח שנה.\n\n"
                                "**מספרים:**\n"
                                f"- שנת דוח {_md(latest_y)}: בערך {_md(f'{dso_l:.0f}')} ימים.\n"
                                f"- שנת דוח {_md(prior_y)}: בערך {_md(f'{dso_p:.0f}')} ימים.\n"
                                f"- שינוי: {_md(f'{change * 100:.0f}%')} (סף אזהרה: {_md('>12%')}).\n\n"
                                "**נוסחה (הערכה גסה):**\n\n"
                                f"{_md('(Receivables / Revenue) * 365')}\n\n"
                                "**למה זה מדאיג:**\n"
                                "- גבייה איטית יותר.\n"
                                "- השוו לענף ולדוח המלא."
                            ),
                            explain={
                                "latest_year": latest_y,
                                "prior_year": prior_y,
                                "receivables_latest": float(ar_l),
                                "receivables_prior": float(ar_p),
                                "revenue_latest": float(rev_l),
                                "revenue_prior": float(rev_p),
                                "dso_latest": float(dso_l),
                                "dso_prior": float(dso_p),
                                "change_pct": float(change * 100.0),
                                "thresholds": {"dso_change_pct_gt": 12.0},
                            },
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
        (
            "LongTermDebtNoncurrent",
            "LongTermDebtAndCapitalLeaseObligations",
            "LongTermDebt",
            "LongTermDebtNoncurrentNetOfUnamortizedDiscountPremiumAndDebtIssuanceCosts",
            "DebtNoncurrent",
            "SecuredLongTermDebt",
            "UnsecuredLongTermDebt",
        ),
    )
    cl_map = _first_tag_map(facts, "us-gaap", ("LiabilitiesCurrent",))
    total_liab_map = _first_tag_map(facts, "us-gaap", ("Liabilities",))

    for yk, lab in ((latest_y, "Net Income"), (prior_y, "Net Income")):
        v = _get_year(by_year, yk, lab)
        if v is not None and yk not in ni_map:
            ni_map[yk] = v
    for yk in (latest_y, prior_y):
        v = _get_year(by_year, yk, "Operating Cash Flow")
        if v is not None and yk not in ocf_map:
            ocf_map[yk] = v

    for yk in (latest_y, prior_y):
        v = _get_year(by_year, yk, "Current Liabilities")
        if v is not None and yk not in cl_map:
            cl_map[yk] = v
        v2 = _get_year(by_year, yk, "Total Liabilities")
        if v2 is not None and yk not in total_liab_map:
            total_liab_map[yk] = v2

    if not rec:
        m_score, err, lvgi_note, m_explain = None, (
            "אין מפת " + _md("Receivables") + " מספיקה ל־" + _md("Beneish")
        ), None, {}
    else:
        m_score, err, lvgi_note, m_explain = _beneish_m_score(
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
            total_liab_map,
        )
    if m_score is not None:
        manipulator_zone = m_score > -1.78
        detail_parts = [
            f"- מודל {_md('Beneish')}: מעריך **הסתברות** למניפולציה ברווחים — **לא** הוכחה.\n"
            "- מבוסס דיווחים שנתיים.\n\n"
            "**סף נפוץ בפרשנות:**\n"
            f"- מעל {_md('-1.78')} → לרוב אזור **סיכון מוגבר**.\n"
            f"- מתחת ל־{_md('-1.78')} → לרוב נחשב יותר \"צפוי\".\n\n"
            "- לא ייעוץ השקעה — רק אות לבדיקה נוספת.\n",
        ]
        if lvgi_note:
            detail_parts.append("\n" + lvgi_note)
        flags.append(
            ForensicFlagDTO(
                severity="high" if manipulator_zone else "info",
                code="beneish_m",
                title_he=f"{_md('Beneish')} {_md('M-Score')} ≈ {_md(f'{m_score:.3f}')}",
                detail_he="".join(detail_parts),
                explain=m_explain,
            )
        )
    elif err:
        flags.append(
            ForensicFlagDTO(
                severity="info",
                code="beneish_skip",
                title_he=f"{_md('Beneish')} — לא חושב (חסרים נתונים)",
                detail_he=(
                    f"- לא חישבנו {_md('Beneish')} — חסרים שדות שנתיים.\n"
                    f"- לדוגמה: {_md('Revenue')}, {_md('Receivables')}.\n\n"
                    f"**פירוט טכני:**\n{err}"
                ),
                explain={"error": err},
            )
        )

    if not flags:
        flags.append(
            ForensicFlagDTO(
                severity="info",
                code="no_major_flags",
                title_he="לא זוהו דגלים חזקים מהבדיקות האוטומטיות",
                detail_he=(
                    "- לא נמצאו דפוסים חזקים מול:\n"
                    f"  - איכות רווח מול {_md('CFO')}.\n"
                    f"  - התארכות {_md('DSO')}.\n"
                    f"  - {_md('Beneish')} חריג.\n"
                    "- זה **לא** אומר שהדוח \"נקי\"."
                ),
            )
        )

    return flags
