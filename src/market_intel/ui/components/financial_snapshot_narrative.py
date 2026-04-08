"""Dynamic Hebrew 'what this screen means' narratives for Fundamentals and Peer Comparison."""

from __future__ import annotations

import math
from typing import Any

import streamlit as st

from market_intel.ui.components.explanation_blocks import formula_row, render_focus_block, render_focus_heading
from market_intel.ui.formatters.bidi_text import ltr_embed as L
from market_intel.ui.formatters.usd_compact import format_usd_compact


def _f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _income_series(inc: list[Any], label: str) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    for r in inc:
        if not isinstance(r, dict):
            continue
        if r.get("label") != label:
            continue
        v = _f(r.get("value"))
        if v is None:
            continue
        try:
            y = int(r.get("fiscal_year", 0))
        except (TypeError, ValueError):
            continue
        out.append((y, v))
    out.sort(key=lambda t: t[0])
    return out


def _fmt_pct(x: float | None, *, digits: int = 1) -> str:
    if x is None:
        return "לא זמין"
    return f"{x * 100:.{digits}f}%"


def _fmt_num(x: float | None, *, digits: int = 2) -> str:
    if x is None:
        return "לא זמין"
    return f"{x:.{digits}f}"


def _bucket3(v: float | None, *, low: float, high: float) -> str:
    """
    3-bucket label:
    - v < low  => 'נמוך/מתחת'
    - v > high => 'גבוה/מעל'
    - else     => 'ביניים'
    """
    if v is None:
        return "לא ברור"
    if v < low:
        return "מתחת"
    if v > high:
        return "מעל"
    return "ביניים"


def _verdict_roic_vs_wacc(*, roic: float | None, wacc: float | None) -> tuple[str, str]:
    """
    Returns (equation_line, verdict_text)
    roic/wacc are fractions (e.g., 0.12 = 12%).
    """
    if roic is None or wacc is None:
        return ("ROIC − WACC = לא זמין", "לא ברור (חסרים נתונים)")
    diff = roic - wacc
    eq = f"ROIC − WACC = {_fmt_pct(diff, digits=2)}"
    # thresholds in absolute pct points
    if diff >= 0.02:
        return (eq, "יוצר ערך (ROIC מעל WACC)")
    if diff <= -0.02:
        return (eq, "לא יוצר ערך (ROIC מתחת WACC)")
    return (eq, "ביניים / מעורב (פער קטן)")


def _verdict_piotroski(p: int | None) -> str:
    if p is None:
        return "לא ברור (אין ציון)"
    if p >= 7:
        return "חיזוק (חזק)"
    if p >= 4:
        return "ביניים"
    return "חלש"


def _verdict_mos(mos_pct: float | None) -> str:
    if mos_pct is None:
        return "לא ברור (אין MOS)"
    if mos_pct >= 15:
        return "יש מרווח (הנחה במודל)"
    if mos_pct <= -15:
        return "יקר במודל"
    return "ביניים / קרוב למודל"


def build_fundamentals_narrative_lines(dash: dict[str, Any]) -> list[str]:
    """
    Pedagogical order: (a) frame + ticker (b) WACC (c) ROIC vs WACC (d) Piotroski
    (e) DCF base + terminal + MOS (f) revenue / NI trends in compact USD (g) disclaimer.
    Altman Z is demoted to the Fundamentals page expander — not repeated here.
    """
    lines: list[str] = []
    sym = str(dash.get("symbol", "?")).upper()
    kfy = dash.get("kpi_fiscal_year")

    fy_note = f" (שנת כספים אחרונה בדוח: **{kfy}**)" if kfy is not None else ""
    lines.append(
        f"**מה מוצג כאן עבור `{L(sym)}`:** דוחות הכנסות, מאזן ותזרים מ־דיווחי "
        f"**{L('SEC')} {L('XBRL')}**, יחד עם **מודל {L('DCF')} פנימי לימודי** שמחשב "
        f"**הערכת שווי** — לא «מחיר אמת» בשוק.{fy_note}"
    )

    wacc_pct = float(dash.get("wacc") or 0) * 100.0
    lines.append(
        f"**{L('WACC')}** — בפרודקט הזה זה **שיעור ההיוון המשוקלל** שבו המערכת **מנכה** "
        f"(מביאה להווה) תזרימי מזומן חופשי צפויים במודל **{L('DCF')}**. "
        f"במודל הבסיסי כרגע: **{wacc_pct:.2f}%**."
    )

    roic = _f(dash.get("roic_latest"))
    if roic is not None:
        rv = roic * 100.0
        diff = rv - wacc_pct
        lines.append(
            f"**{L('ROIC')}** — תשואה על ההון המושקע בפעילות בשנה האחרונה שחושבה כאן; "
            f"משמשת להשוואה ל־**{L('WACC')}** (עלות ההון לפי המודל). "
            f"**{L('ROIC')}** ≈ **{rv:.2f}%** ⇒ פער מול **{L('WACC')}**: **{diff:+.2f} נק׳**."
        )
        if diff > 2.0:
            lines.append(
                "פער **חיובי** משמעותי — לרוב מפרשים **יצירת ערך גסה** מהפעילות "
                "ביחס לעלות ההון (במסגרת המודל)."
            )
        elif diff < -2.0:
            lines.append(
                "פער **שלילי** משמעותי — לרוב מפרשים שהפעילות **מתקשה לכסות** את עלות ההון; "
                "כדאי לבדוק מגזר, מחזור והשקעות."
            )
        else:
            lines.append("הפער קטן — תמונה **מעורבת**, בלי סיפור חד־משמעי של יצירת/השמדת ערך.")

    pi = dash.get("piotroski_score")
    if pi is not None:
        try:
            p = int(pi)
        except (TypeError, ValueError):
            p = None
        if p is not None:
            if p >= 7:
                lines.append(
                    f"**{L('Piotroski')} F = {p}/9** — ציון **איכות/שיפור** מול שנה קודמת; "
                    "כאן נחשב **חזק** יחסית."
                )
            elif p >= 4:
                lines.append(
                    f"**{L('Piotroski')} F = {p}/9** — אזור **בינוני**; "
                    "כדאי לעבור דגלים בפירוט אם קיימים."
                )
            else:
                lines.append(
                    f"**{L('Piotroski')} F = {p}/9** — **נמוך**; "
                    "דורש הקשר (מגזר, שנה חריגה, חשבונאות)."
                )

    dcf_base = dash.get("dcf_base")
    if not isinstance(dcf_base, dict):
        dcf_base = {}
    tg_pct = float(dcf_base.get("terminal_growth") or 0) * 100.0
    lines.append(
        f"**{L('DCF')} (מודל בסיס)** — **הערכת שווי פנימית** מברירת־מחדל: "
        f"תזרים מזומן חופשי בסיסי, צמיחה בשלב מפורש, ו־**{L('Terminal growth')}** = "
        "צמיחה ארוכת־טווח **לנצח** בשלב גורדון "
        f"(כרגע **{tg_pct:.2f}%**; חייבת להישאר **מתחת** ל־**{L('WACC')}** "
        "כדי שהנוסחה תהיה הגיונית)."
    )

    intrinsic = _f(dcf_base.get("intrinsic_per_share"))
    ev = _f(dcf_base.get("enterprise_value"))
    mp = _f(dash.get("market_price"))
    if intrinsic is not None and mp is not None and mp > 0:
        lines.append(
            f"מהמודל הבסיסי יוצא **מחיר הוגן למניה** ~**{intrinsic:.2f} {L('USD')}** "
            f"מול **מחיר שוק** ~**{mp:.2f} {L('USD')}**."
        )
    elif intrinsic is not None:
        lines.append(
            f"**מחיר הוגן למניה** (בסיס): כ־**{intrinsic:.2f} {L('USD')}**."
        )
    if ev is not None:
        ev_s = format_usd_compact(ev)
        lines.append(
            f"**שווי עסק ({L('Enterprise Value')})** לפי אותו מודל בסיס: סביב **{ev_s}**."
        )

    mos = _f(dash.get("margin_of_safety_pct"))
    if mos is not None:
        if mos > 15.0:
            lines.append(
                f"**{L('MOS')} (מרווח ביטחון)** ≈ **{mos:+.1f}%** — המניה **מתחת** "
                f"להערכת ה־**{L('DCF')}** לפי המודל; לא המלצה, המודל עלול לטעות."
            )
        elif mos < -15.0:
            lines.append(
                f"**{L('MOS')}** ≈ **{mos:+.1f}%** — המחיר **מעל** ההערכה; "
                "ייתכן צמיחה, איכות, או הנחות מודל שלא מתאימות."
            )
        else:
            lines.append(
                f"**{L('MOS')}** ≈ **{mos:+.1f}%** — קרוב להערכת הבסיס; "
                "אין פער קיצוני במודל הפנימי."
            )

    inc = dash.get("income") or []
    rev = _income_series(inc, "Revenue")
    if len(rev) >= 2:
        y0, v0 = rev[0]
        y1, v1 = rev[-1]
        ny = max(y1 - y0, 1)
        cagr = ((v1 / v0) ** (1.0 / ny) - 1.0) * 100.0 if v0 > 0 else None
        lines.append(
            f"**מגמת הכנסות ({L('Revenue')}):** **{y0}** → **{y1}**: "
            f"**{format_usd_compact(v0)}** ל־**{format_usd_compact(v1)}** (דולרים מדווחים)."
        )
        if cagr is not None:
            lines.append(
                f"קירוב **{L('CAGR')}** גאומטרי על **{ny}** שנים: **{cagr:+.1f}%** לשנה "
                "(אם יש חורים בשנים — קירוב בלבד)."
            )
    ni = _income_series(inc, "Net Income")
    if len(ni) >= 2:
        y_a, nv0 = ni[0]
        y_b, nv1 = ni[-1]
        lines.append(
            f"**רווח נקי ({L('Net Income')}):** **{y_a}** → **{y_b}**: "
            f"**{format_usd_compact(nv0)}** ל־**{format_usd_compact(nv1)}** — "
            "בדוק עקביות מול פריטים חד־פעמיים."
        )

    lines.append(
        f"**לסיכום:** המסך משלב **דיווחים** עם **מודל {L('DCF')} לימודי** — לא חיזוי מחיר, "
        "לא תחליף להשוואת מתחרים או לסיכון האישי שלך."
    )
    return lines


def render_fundamentals_snapshot(dash: dict[str, Any]) -> None:
    lines = build_fundamentals_narrative_lines(dash)
    if not lines:
        return

    sym = str(dash.get("symbol", "?")).strip().upper()
    kfy = dash.get("kpi_fiscal_year")

    render_focus_heading(f"**{sym}** — סדר פעולות (שורה־שורה, לפי המספרים למעלה)", variant="steps")
    st.caption("כל בלוק צבוע כדי למקד; נוסחאות בשורה נפרדת. פירוט יבש ב‑Advanced.")

    roic = _f(dash.get("roic_latest"))
    wacc = _f(dash.get("wacc"))
    pi_raw = dash.get("piotroski_score")
    try:
        pi = int(pi_raw) if pi_raw is not None else None
    except (TypeError, ValueError):
        pi = None
    mos = _f(dash.get("margin_of_safety_pct"))

    eq_roic, verdict_roic = _verdict_roic_vs_wacc(roic=roic, wacc=wacc)
    verdict_pio = _verdict_piotroski(pi)
    verdict_mos = _verdict_mos(mos)

    inc = dash.get("income") or []
    rev = _income_series(inc, "Revenue")
    ni = _income_series(inc, "Net Income")
    rev_trend = None
    if len(rev) >= 2 and rev[0][1] > 0:
        rev_trend = (rev[-1][1] / rev[0][1]) - 1.0
    ni_trend = None
    if len(ni) >= 2 and ni[0][1] != 0:
        ni_trend = (ni[-1][1] - ni[0][1])

    rev_label = (
        "תומכת"
        if rev_trend is not None and rev_trend > 0.10
        else "לא תומכת"
        if rev_trend is not None and rev_trend < -0.10
        else "ביניים"
        if rev_trend is not None
        else "לא ברור"
    )
    ni_label = (
        "תומכת"
        if ni_trend is not None and ni_trend > 0
        else "לא תומכת"
        if ni_trend is not None and ni_trend < 0
        else "ביניים"
        if ni_trend is not None
        else "לא ברור"
    )

    roic_txt = _fmt_pct(roic, digits=2) if roic is not None else "לא זמין"
    wacc_txt = _fmt_pct(wacc, digits=2) if wacc is not None else "לא זמין"
    mos_txt = f"{mos:+.1f}%" if mos is not None else "לא זמין"

    fy_line = f"שנת הדוח האחרונה שמוצגת כאן: **{kfy}**.\n" if kfy is not None else ""
    render_focus_block(
        f"**פתיחה — רק על {sym}**\n"
        f"{fy_line}"
        "לא מדובר במדריך גנרי: כל משפט למטה נשען על **המספרים שבמסך הזה**.\n"
        "איך לקרוא: שורה אחת = רעיון אחד. אחרי נוסחה — עוצרים ומסתכלים על המספרים שוב.",
        variant="steps",
    )

    render_focus_block(
        f"**שלב 1 — האם העסק מייצר ערך מעל עלות ההון?**\n"
        f"עבור **{sym}**: **ROIC** מול **WACC** מהמודל.\n"
        f"מה המספרים אומרים כאן: ROIC = **{roic_txt}**, WACC = **{wacc_txt}**.\n"
        f"השוואה מהירה: {eq_roic}\n"
        f"**פסק דין לשלב הזה:** {verdict_roic}\n"
        "**נוסחה (רעיון, באחוזים):**\n"
        f"{formula_row('ROIC% − WACC%')}",
        variant="neutral",
    )

    pi_disp = "לא זמין" if pi is None else str(pi)
    render_focus_block(
        f"**שלב 2 — יציבות ושיפור (Piotroski)**\n"
        f"עבור **{sym}**: ציון **{pi_disp}** מתוך **9**.\n"
        f"**פסק דין:** {verdict_pio}\n"
        "אם הציון נמוך: לא בהכרח «מניה רעה» — לפעמים שנה חריגה או מגזר; כן צריך לפתוח דגלים.",
        variant="steps",
    )

    render_focus_block(
        f"**שלב 3 — המחיר מול מודל ה־DCF שמוצג כאן (MOS)**\n"
        f"עבור **{sym}**: מרווח הביטחון ≈ **{mos_txt}**.\n"
        f"**פסק דין:** {verdict_mos}\n"
        "**נוסחה (רעיון):**\n"
        f"{formula_row('MOS ≈ (Intrinsic − Price) / Intrinsic  (במודל הפנימי)')}",
        variant="neutral",
    )

    render_focus_block(
        f"**שלב 4 — האם הדוחות «תומכים» בסיפור? (מגמה רב־שנתית)**\n"
        f"עבור **{sym}**: קריאה מהירה על **Revenue** ו־**Net Income** בטבלאות למעלה.\n"
        f"התיוג האוטומטי כאן: הכנסות **{rev_label}**, רווח נקי **{ni_label}**.\n"
        "לא מסיקים מזה צו קנייה — רק אם המודל והמכפילים מקבלים גב או סתירה.",
        variant="caution",
    )

    render_focus_block(
        "**מה עושים אחרי ארבעת השלבים?**\n"
        f"אם איכות חלשה — **{sym}** דורשת קודם תזרים, חוב ודוחות, לא רק מכפיל.\n"
        "אם איכות חזקה ו־MOS נוח — הגיוני לעבור ל־**Peer Comparison** ולבדוק אם הפרמיה מוצדקת.\n"
        "אם הכל באמצע — בוחרים **נקודת ביקורת אחת** (דוח הבא / מרג’ין / תחרות) וממתינים לנתון מכריע.",
        variant="insight",
    )

    with st.expander("Advanced — פירוט מקצועי מהנתונים", expanded=False):
        st.markdown("#### פירוט (מקצועי/יבש)")
        st.caption(
            f"סדר קבוע: מסגרת → {L('WACC')} → {L('ROIC')} → {L('Piotroski')} → "
            f"{L('DCF')} / {L('Terminal growth')} / {L('MOS')} → מגמות הכנסות ורווח נקי. "
            f"{L('Altman Z')} במפתח למטה. לא המלצה."
        )
        render_focus_block("\n\n".join(f"- {line}" for line in lines), variant="neutral")
        st.caption("לא ייעוץ השקעות.")


def render_forensic_analyst_alerts(dash: dict[str, Any]) -> None:
    """Red-flag forensic block from backend `forensic_flags`."""
    raw = dash.get("forensic_flags") or []
    if not raw:
        return
    st.markdown("### 🚨 אזהרות אנליסט — פורנזיקה חשבונאית (אוטומטי)")
    st.caption(
        f"היוריסטיקות על דוחות ו־**{L('XBRL')}** — לא ביקורת מאושרת, "
        "לא ייעוץ משפטי או השקעות."
    )
    high = [f for f in raw if isinstance(f, dict) and f.get("severity") == "high"]
    medium = [f for f in raw if isinstance(f, dict) and f.get("severity") == "medium"]
    info = [f for f in raw if isinstance(f, dict) and f.get("severity") == "info"]

    def _one(flag: dict[str, Any]) -> None:
        title = flag.get("title_he", "")
        detail = flag.get("detail_he", "")
        render_focus_block(f"**{title}**\n\n{detail}", variant="neutral")
        explain = flag.get("explain")
        if isinstance(explain, dict) and explain:
            with st.expander("Explain — חישוב ביניים (שקיפות)", expanded=False):
                st.json(explain)

    for f in high:
        with st.container():
            title = str(f.get("title_he") or "סיכון גבוה")
            detail = str(f.get("detail_he") or "")
            body = f"**דגל אדום — {title}**" + (f"\n\n{detail}" if detail else "")
            render_focus_block(body, variant="caution")
            explain = f.get("explain")
            if isinstance(explain, dict) and explain:
                with st.expander("Explain — חישוב ביניים (שקיפות)", expanded=False):
                    st.json(explain)
    for f in medium:
        with st.container():
            mt = str(f.get("title_he") or "")
            md = str(f.get("detail_he") or "")
            body = "**אזהרה**" + (f" — {mt}" if mt else "") + (f"\n\n{md}" if md else "")
            render_focus_block(body, variant="steps")
            explain = f.get("explain")
            if isinstance(explain, dict) and explain:
                with st.expander("Explain — חישוב ביניים (שקיפות)", expanded=False):
                    st.json(explain)
    if info:
        with st.expander("מידע נוסף / תוצאות Beneish וסטטוס בדיקה", expanded=False):
            for f in info:
                _one(f)
                st.divider()


def _peer_numeric_list(rows: list[dict[str, Any]], key: str, exclude_subject: bool) -> list[float]:
    out: list[float] = []
    for r in rows:
        if exclude_subject and r.get("is_subject"):
            continue
        v = _f(r.get(key))
        if v is not None:
            out.append(v)
    return out


def _rank_approx(value: float, others: list[float]) -> tuple[int, int]:
    """How many strictly below / total (for 'richer than X% of peers')."""
    if not others:
        return 0, 0
    below = sum(1 for x in others if x < value)
    return below, len(others)


def build_peer_narrative_lines(
    rows: list[dict[str, Any]],
    subject: dict[str, Any],
    avg: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    sym = str(subject.get("symbol", "?"))
    comps = [r for r in rows if not r.get("is_subject")]
    lines.append(
        f"הניתוח הבא מתייחס ל־**{sym}** מול **{len(comps)}** "
        "שורות מתחרים בטבלה (בלי שורת הממוצע) — "
        "אם הזנת מתחרים ידנית, הם חלק מהקבוצה."
    )
    pe_s = _f(subject.get("pe_ratio"))
    pe_o = _peer_numeric_list(rows, "pe_ratio", exclude_subject=True)
    pe_a = _f(avg.get("pe_ratio"))

    if pe_s is not None and pe_o:
        b, t = _rank_approx(pe_s, pe_o)
        pct = (b / t * 100.0) if t else 0.0
        lines.append(
            f"**P/E** של **{sym}** = **{pe_s:.1f}**. מתוך המתחרים בטבלה, "
            f"**{b}** עם P/E **נמוך יותר** (כ־{pct:.0f}% מהשורות) — "
            "כלומר אתה **לא** בהכרח בתחתית המכפילים."
        )
    if pe_s is not None and pe_a is not None and pe_a > 0:
        rel = (pe_s - pe_a) / pe_a * 100.0
        lines.append(
            f"מול **ממוצע הקבוצה** בטבלה: P/E **{rel:+.1f}%** מהממוצע (**{pe_a:.1f}**)."
        )

    ev_s = _f(subject.get("ev_ebitda"))
    ev_o = _peer_numeric_list(rows, "ev_ebitda", exclude_subject=True)
    ev_a = _f(avg.get("ev_ebitda"))
    if ev_s is not None and ev_a is not None and ev_a > 0:
        rel_e = (ev_s - ev_a) / ev_a * 100.0
        lines.append(
            f"**EV/EBITDA** של **{sym}** = **{ev_s:.1f}** לעומת ממוצע **{ev_a:.1f}** "
            f"(**{rel_e:+.1f}%**) — מכפיל תפעולי יחסי; שימושי כשיש הבדלי מינוף."
        )
    if ev_s is not None and ev_o:
        b2, t2 = _rank_approx(ev_s, ev_o)
        lines.append(
            f"ביחס למתחרים: **{b2}** מתוך **{t2}** עם EV/EBITDA **נמוך יותר** מ־{sym}."
        )

    om_s = _f(subject.get("operating_margin"))
    om_o = _peer_numeric_list(rows, "operating_margin", exclude_subject=True)
    om_a = _f(avg.get("operating_margin"))
    if om_s is not None and om_a is not None:
        lines.append(
            f"**שולי רווח תפעולי** — **{sym}**: **{om_s * 100:.1f}%**, "
            f"ממוצע הקבוצה: **{om_a * 100:.1f}%** "
            f"({'מעל הממוצע' if om_s > om_a else 'מתחת לממוצע' if om_s < om_a else 'ליד הממוצע'})."
        )
    if om_s is not None and om_o:
        higher_om = sum(1 for x in om_o if x > om_s)
        lines.append(
            f"**מרג’ין תפעולי:** **{higher_om}** מתוך **{len(om_o)}** מתחרים "
            f"עם מרג’ין **גבוה יותר** מ־{sym}."
        )

    rg_s = _f(subject.get("revenue_growth"))
    rg_a = _f(avg.get("revenue_growth"))
    if rg_s is not None and rg_a is not None:
        lines.append(
            f"**צמיחת הכנסות (YoY)** — **{sym}**: **{rg_s * 100:.1f}%**, "
            f"ממוצע: **{rg_a * 100:.1f}%**. "
            "שילוב עם P/E גבוה: לעיתים \"מוצדק\" אם הצמיחה חזקה; "
            "P/E גבוה עם צמיחה חלשה — **מתיחה יחסית**."
        )

    zpe = _f(subject.get("z_pe_ratio"))
    zev = _f(subject.get("z_ev_ebitda"))
    if zpe is not None:
        zone = (
            "מעל הממוצע הסטטיסטי של הקבוצה"
            if zpe > 0.5
            else "מתחת לממוצע" if zpe < -0.5 else "ליד הממוצע"
        )
        lines.append(
            f"**Z-Score ל־P/E** (יחסית לממוצע והתפלגות בטבלה): **{zpe:+.2f}** — {zone}."
        )
    if zev is not None:
        lines.append(
            f"**Z-Score ל־EV/EBITDA**: **{zev:+.2f}** — "
            "מדד לחריגות מכפיל תפעולי בתוך אותה קבוצת השוואה."
        )

    if (
        pe_s is not None
        and pe_a is not None
        and pe_a > 0
        and rg_s is not None
        and rg_a is not None
        and abs(rg_a) > 1e-6
    ):
        prem = (pe_s - pe_a) / pe_a * 100.0
        mult = rg_s / rg_a
        if prem > 8 and mult >= 1.8:
            lines.append(
                f"**תמחור יחסי מול צמיחה:** המניה נסחרת ב**פרמיה** "
                f"של כ־**{prem:.0f}%** על ממוצע הקבוצה, "
                f"אבל צמיחת ההכנסות מהירה בכ־**{mult:.1f}×** מהממוצע — "
                "לעיתים השוק \"משלם\" על צמיחה יחסית חזקה."
            )
        elif prem < -8 and mult < 0.85:
            lines.append(
                f"**הנחה יחסית עם צמיחה חלשה:** P/E נמוך בכ־**{abs(prem):.0f}%** "
                "מהממוצע וצמיחה **מתחת** לממוצע "
                f"(**{mult:.2f}×**) — לעיתים סיטואציה של לחץ על הסקטור "
                "או ספקות לגבי הסיפור העסקי."
            )

    lines.append(
        "**מה כאן לא נותן תשובה סופית:** האם המניה «זולה» או «יקרה» באופן "
        "מוחלט — חסרים עסקאות עתידיות, איכות הנהלה, רגולציה והבדלי חשבונאות בין מדינות. "
        "הטבלה נותנת רק **השוואה יחסית** בתוך קבוצת המתחרים שבחרת."
    )
    lines.append(
        "**לסיכום פרקטי:** חפשו **עקביות** — מכפיל נמוך + מרג’ין גבוה + צמיחה סבירה = "
        "תרחיש שנלמד עליו כ\"פער אפשרי\"; ההפך דורש הסבר (מיתון, סיכון, סקטור)."
    )
    return lines


def render_peer_snapshot(
    rows: list[dict[str, Any]],
    subject: dict[str, Any],
    avg: dict[str, Any],
) -> None:
    lines = build_peer_narrative_lines(rows, subject, avg)
    if not lines:
        return
    sym = str(subject.get("symbol", "?")).strip().upper()
    n_peers = max(0, len([r for r in rows if not r.get("is_subject")]))

    render_focus_heading(f"**{sym}** מול **{n_peers}** שורות בטבלה — שלושה שלבים", variant="steps")
    st.caption("בלוקים צבעוניים = מיקוד; כל שלב בנוי מהמספרים של **המניה שלך** מול ממוצע הקבוצה.")

    pe = _f(subject.get("pe_ratio"))
    pe_avg = _f(avg.get("pe_ratio"))
    ev = _f(subject.get("ev_ebitda"))
    ev_avg = _f(avg.get("ev_ebitda"))
    om = _f(subject.get("operating_margin"))
    om_avg = _f(avg.get("operating_margin"))
    rg = _f(subject.get("revenue_growth"))
    rg_avg = _f(avg.get("revenue_growth"))

    pe_rel = None
    if pe is not None and pe_avg is not None and pe_avg > 0:
        pe_rel = (pe - pe_avg) / pe_avg
    ev_rel = None
    if ev is not None and ev_avg is not None and ev_avg > 0:
        ev_rel = (ev - ev_avg) / ev_avg

    price_bucket = _bucket3(pe_rel, low=-0.10, high=0.10)
    ev_bucket = _bucket3(ev_rel, low=-0.10, high=0.10)

    quality_bucket = "לא ברור"
    if om is not None and om_avg is not None and rg is not None and rg_avg is not None:
        better_quality = om > om_avg
        better_growth = rg > rg_avg
        if better_quality and better_growth:
            quality_bucket = "מוסבר"
        elif (not better_quality) and (not better_growth):
            quality_bucket = "לא מוסבר"
        else:
            quality_bucket = "לא חד"

    render_focus_block(
        f"**שלב 1 — תמחור יחסי (רק בהשוואה לקבוצה שבחרת)**\n"
        f"עבור **{sym}**:\n"
        f"- **P/E** = **{_fmt_num(pe, digits=1)}** (ממוצע בטבלה: **{_fmt_num(pe_avg, digits=1)}**)\n"
        f"- **EV/EBITDA** = **{_fmt_num(ev, digits=1)}** (ממוצע: **{_fmt_num(ev_avg, digits=1)}**)\n"
        f"**פסק דין מהיר:** P/E ביחס לממוצע — **{price_bucket}**; EV/EBITDA — **{ev_bucket}**.\n"
        "**נוסחאות (רעיון):**\n"
        f"{formula_row('P/E = Price / EPS')}"
        f"{formula_row('EV/EBITDA = Enterprise Value / EBITDA')}",
        variant="neutral",
    )

    render_focus_block(
        f"**שלב 2 — האם «הסיפור העסקי» מסביר את המכפיל?**\n"
        f"עבור **{sym}**:\n"
        f"- **שולי תפעול** = **{_fmt_pct(om, digits=1)}** (ממוצע קבוצה **{_fmt_pct(om_avg, digits=1)}**)\n"
        f"- **צמיחת הכנסות (YoY)** = **{_fmt_pct(rg, digits=1)}** (ממוצע **{_fmt_pct(rg_avg, digits=1)}**)\n"
        f"**פסק דין:** {quality_bucket} — כלומר האם פרמיה/הנחה «יושבות» על איכות וצמיחה יחסית.",
        variant="steps",
    )

    render_focus_block(
        "**שלב 3 — מה עושים עם המידע הזה?**\n"
        f"אם **{sym}** זולה יחסית אבל איכות+צמיחה חלשות — חושבים על **מלכודת ערך**.\n"
        "אם יקרה יחסית אבל איכות+צמיחה חזקות — לפעמים זו **פרמיה מוסברת**.\n"
        "אם לא ברור — בוחרים **נתון אחד** שישבור שוויון (דוח / מרג’ין / חוב) לפני החלטה.",
        variant="insight",
    )

    with st.expander("Advanced — פירוט מקצועי מהטבלה", expanded=False):
        st.caption("דירוגים ויחסים מהנתונים שמוצגים — לא צו קנייה/מכירה.")
        render_focus_block("\n\n".join(f"- {line}" for line in lines), variant="neutral")
        st.caption("לא ייעוץ השקעות.")
