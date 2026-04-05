"""Dynamic Hebrew 'what this screen means' narratives for Fundamentals and Peer Comparison."""

from __future__ import annotations

import math
from typing import Any

import streamlit as st


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


def build_fundamentals_narrative_lines(dash: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    wacc_pct = float(dash.get("wacc") or 0) * 100.0
    lines.append(
        f"**WACC (מודל)** = **{wacc_pct:.2f}%** — זה קצב ההיוון שבו המערכת מנכה את התזרימים העתידיים ב־DCF, לפי ההנחות שמסתתרות מאחורי המספר."
    )

    roic = _f(dash.get("roic_latest"))
    if roic is not None:
        rv = roic * 100.0
        diff = rv - wacc_pct
        lines.append(
            f"**ROIC (שנה אחרונה)** ≈ **{rv:.2f}%**. מול WACC זה פער של **{diff:+.2f} נקודות אחוז**."
        )
        if diff > 2.0:
            lines.append(
                "יש פער **חיובי** משמעותי בין השניים. לפי המסגרת של המודל, לרוב מפרשים את זה כ־**יצירת ערך** מהפעילות ביחס לעלות ההון."
            )
        elif diff < -2.0:
            lines.append(
                "יש פער **שלילי** משמעותי. לפי המסגרת של המודל, לרוב מפרשים שהפעילות **לא מכסה** ביציבות את עלות ההון — שווה לבדוק למה (מחזור, השקעות, מגזר)."
            )
        else:
            lines.append(
                "הפער סביב ה־WACC **קטן** — תמונה **מעורבת**, בלי סיפור חד־משמעי של יצירת ערך או השמדת ערך גסה."
            )

    pi = dash.get("piotroski_score")
    if pi is not None:
        try:
            p = int(pi)
        except (TypeError, ValueError):
            p = None
        if p is not None:
            if p >= 7:
                lines.append(
                    f"**Piotroski F = {p}/9** — לרוב נחשב **חזק** (איכות/שיפור פיננסי יחסית לשנה קודמת)."
                )
            elif p >= 4:
                lines.append(
                    f"**Piotroski F = {p}/9** — אזור **בינוני**; אם יש פירוט דגלים ב־API, שווה לעבור שורה־שורה."
                )
            else:
                lines.append(
                    f"**Piotroski F = {p}/9** — **נמוך** לפי הסקאלה; דורש הקשר (שנה חריגה, מגזר, עסקאות, שינוי חתך דיווח)."
                )

    az = _f(dash.get("altman_z"))
    if az is not None:
        if az >= 2.99:
            lines.append(
                f"**Altman Z ≈ {az:.2f}** — בתחום שמסווגים לרוב כ־**בטוח יחסית** למצוקה (מודל קלאסי לתעשייה; לא תחליף לניתוח חוב)."
            )
        elif az >= 1.81:
            lines.append(
                f"**Altman Z ≈ {az:.2f}** — **אזור אפור**; ערבוב סימנים — כדאי לשלב נזילות, חוב ותזרים."
            )
        else:
            lines.append(
                f"**Altman Z ≈ {az:.2f}** — **מתחת ל־1.81** — מסווג לרוב כאזור **סיכון מצוקה**; לא אסון מוכרז, אבל **דגל לבדיקה עמוקה**."
            )

    dcf_base = dash.get("dcf_base")
    if not isinstance(dcf_base, dict):
        dcf_base = {}
    intrinsic = _f(dcf_base.get("intrinsic_per_share"))
    mp = _f(dash.get("market_price"))
    if intrinsic is not None and mp is not None and mp > 0:
        lines.append(
            f"**DCF בסיס (מודל)** נותן הערכת **מחיר הוגן למניה** של סביב **{intrinsic:.2f}** דולר, "
            f"מול **מחיר שוק** ~**{mp:.2f}** (כפי שנמשך כאן)."
        )
    mos = _f(dash.get("margin_of_safety_pct"))
    if mos is not None:
        if mos > 15.0:
            lines.append(
                f"**מרווח ביטחון (MOS)** ≈ **{mos:+.1f}%** — לפי המודל הבסיסי, המניה נסחרת **מתחת** להערכת ה־DCF (לא אומר שצריך לקנות; המודל יכול לטעות)."
            )
        elif mos < -15.0:
            lines.append(
                f"**מרווח ביטחון** ≈ **{mos:+.1f}%** — לפי המודל הבסיסי, המחיר **מעל** ההערכה; יכול להיות צמיחה מחירית, איכות, או הנחות מודל שלא מתאימות."
            )
        else:
            lines.append(
                f"**מרווח ביטחון** ≈ **{mos:+.1f}%** — קרוב להערכה הבסיסית; אין פער דרמטי במודל הפנימי."
            )

    inc = dash.get("income") or []
    rev = _income_series(inc, "Revenue")
    if len(rev) >= 2:
        y0, v0 = rev[0]
        y1, v1 = rev[-1]
        ny = max(y1 - y0, 1)
        cagr = ((v1 / v0) ** (1.0 / ny) - 1.0) * 100.0 if v0 > 0 else None
        lines.append(
            f"**Revenue** ב־**{y0}** לעומת **{y1}**: מ־**{v0:,.0f}** ל־**{v1:,.0f}** (יחידות כפי שדווחו ב־XBRL)."
        )
        if cagr is not None:
            lines.append(
                f"קצב צמיחה **ממוצע גאומטרי גס** על פני {ny} שנים: בערך **{cagr:+.1f}%** לשנה (אם יש שנות חור — זה קירוב בלבד)."
            )
    ni = _income_series(inc, "Net Income")
    if len(ni) >= 2:
        y_a, nv0 = ni[0]
        y_b, nv1 = ni[-1]
        lines.append(
            f"**Net Income** בין **{y_a}** ל־**{y_b}** זז מ־**{nv0:,.0f}** ל־**{nv1:,.0f}** — בדוק אם המגמה **עקבית** או מושפעת מפריטים חד־פעמיים."
        )

    lines.append(
        "**לסיכום:** המסך משלב **דיווחים היסטוריים** עם **מודל DCF פנימי**. הוא **לא** חוזה מחיר למחר, ו**לא** מחליף השוואה למתחרים או בחינת סיכון אישית."
    )
    return lines


def render_fundamentals_snapshot(dash: dict[str, Any]) -> None:
    lines = build_fundamentals_narrative_lines(dash)
    if not lines:
        return
    st.markdown("#### בתכלס — מה המספרים **הספציפיים** של החברה אומרים כאן")
    st.caption("פרשנות חינוכית על הנתונים שנטענו מה־API — לא המלצה.")
    st.markdown("\n".join(f"- {line}" for line in lines))
    st.caption("לא ייעוץ השקעות.")


def render_forensic_analyst_alerts(dash: dict[str, Any]) -> None:
    """Red-flag forensic block from backend `forensic_flags`."""
    raw = dash.get("forensic_flags") or []
    if not raw:
        return
    st.markdown("### 🚨 אזהרות אנליסט — פורנזיקה חשבונאית (אוטומטי)")
    st.caption(
        "היוריסטיקות על דוחות ו־XBRL — לא ביקורת מאושרת, לא ייעוץ משפטי או השקעות."
    )
    high = [f for f in raw if isinstance(f, dict) and f.get("severity") == "high"]
    medium = [f for f in raw if isinstance(f, dict) and f.get("severity") == "medium"]
    info = [f for f in raw if isinstance(f, dict) and f.get("severity") == "info"]

    def _one(flag: dict[str, Any]) -> None:
        title = flag.get("title_he", "")
        detail = flag.get("detail_he", "")
        st.markdown(f"**{title}**")
        st.markdown(detail)

    for f in high:
        with st.container():
            st.error("דגל אדום")
            _one(f)
    for f in medium:
        with st.container():
            st.warning("אזהרה")
            _one(f)
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
        f"הניתוח הבא מתייחס ל־**{sym}** מול **{len(comps)}** שורות מתחרים בטבלה (בלי שורת הממוצע) — אם הזנת מתחרים ידנית, הם חלק מהקבוצה."
    )
    pe_s = _f(subject.get("pe_ratio"))
    pe_o = _peer_numeric_list(rows, "pe_ratio", exclude_subject=True)
    pe_a = _f(avg.get("pe_ratio"))

    if pe_s is not None and pe_o:
        b, t = _rank_approx(pe_s, pe_o)
        pct = (b / t * 100.0) if t else 0.0
        lines.append(
            f"**P/E** של **{sym}** = **{pe_s:.1f}**. מתוך המתחרים בטבלה, **{b}** עם P/E **נמוך יותר** (כ־{pct:.0f}% מהשורות) — כלומר אתה **לא** בהכרח בתחתית המכפילים."
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
            f"**EV/EBITDA** של **{sym}** = **{ev_s:.1f}** לעומת ממוצע **{ev_a:.1f}** (**{rel_e:+.1f}%**) — מכפיל תפעולי יחסי; שימושי כשיש הבדלי מינוף."
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
            f"**שולי רווח תפעולי** — **{sym}**: **{om_s * 100:.1f}%**, ממוצע הקבוצה: **{om_a * 100:.1f}%** "
            f"({'מעל הממוצע' if om_s > om_a else 'מתחת לממוצע' if om_s < om_a else 'ליד הממוצע'})."
        )
    if om_s is not None and om_o:
        higher_om = sum(1 for x in om_o if x > om_s)
        lines.append(
            f"**מרג’ין תפעולי:** **{higher_om}** מתוך **{len(om_o)}** מתחרים עם מרג’ין **גבוה יותר** מ־{sym}."
        )

    rg_s = _f(subject.get("revenue_growth"))
    rg_a = _f(avg.get("revenue_growth"))
    if rg_s is not None and rg_a is not None:
        lines.append(
            f"**צמיחת הכנסות (YoY)** — **{sym}**: **{rg_s * 100:.1f}%**, ממוצע: **{rg_a * 100:.1f}%**. "
            "שילוב עם P/E גבוה: לעיתים \"מוצדק\" אם הצמיחה חזקה; P/E גבוה עם צמיחה חלשה — **מתיחה יחסית**."
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
            f"**Z-Score ל־EV/EBITDA**: **{zev:+.2f}** — מדד לחריגות מכפיל תפעולי בתוך אותה קבוצת השוואה."
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
                f"**תמחור יחסי מול צמיחה:** המניה נסחרת ב**פרמיה** של כ־**{prem:.0f}%** על ממוצע הקבוצה, "
                f"אבל צמיחת ההכנסות מהירה בכ־**{mult:.1f}×** מהממוצע — לעיתים השוק \"משלם\" על צמיחה יחסית חזקה."
            )
        elif prem < -8 and mult < 0.85:
            lines.append(
                f"**הנחה יחסית עם צמיחה חלשה:** P/E נמוך בכ־**{abs(prem):.0f}%** מהממוצע וצמיחה **מתחת** לממוצע (**{mult:.2f}×**) — "
                "לעיתים סיטואציה של לחץ על הסקטור או ספקות לגבי הסיפור העסקי."
            )

    lines.append(
        "**מה כאן לא נותן תשובה סופית:** האם המניה «זולה» או «יקרה» באופן מוחלט — חסרים עסקאות עתידיות, איכות הנהלה, רגולציה והבדלי חשבונאות בין מדינות. "
        "הטבלה נותנת רק **השוואה יחסית** בתוך קבוצת המתחרים שבחרת."
    )
    lines.append(
        "**לסיכום פרקטי:** חפשו **עקביות** — מכפיל נמוך + מרג’ין גבוה + צמיחה סבירה = תרחיש שנלמד עליו כ\"פער אפשרי\"; ההפך דורש הסבר (מיתון, סיכון, סקטור)."
    )
    return lines


def render_peer_snapshot(rows: list[dict[str, Any]], subject: dict[str, Any], avg: dict[str, Any]) -> None:
    lines = build_peer_narrative_lines(rows, subject, avg)
    if not lines:
        return
    st.markdown("#### בתכלס — איך **המניה שלך** יושבת בתוך הטבלה הזו")
    st.caption("דירוגים ויחסים מהנתונים שמוצגים — לא צו קנייה/מכירה.")
    st.markdown("\n".join(f"- {line}" for line in lines))
    st.caption("לא ייעוץ השקעות.")
