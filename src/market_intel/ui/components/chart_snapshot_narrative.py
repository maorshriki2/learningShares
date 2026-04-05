"""Practical, data-driven Hebrew interpretation for the chart currently on screen."""

from __future__ import annotations

from typing import Any

import streamlit as st

_TF_CONTEXT: dict[str, str] = {
    "1mo": "כל נר = חודש מסחר אחד. הנר הימני ביותר הוא החודש האחרון בחלון.",
    "1wk": "כל נר = שבוע מסחר אחד (אצל ספק הנתונים לרוב שבוע קלנדרי). הנר הימני ביותר הוא השבוע האחרון בחלון.",
    "1d": "כל נר = יום מסחר אחד. הנר הימני ביותר הוא היום האחרון בחלון.",
    "1h": "כל נר = שעת מסחר אחת. הנר הימני ביותר הוא השעה האחרונה בחלון.",
    "15m": "כל נר = רבע שעה. הנר הימני ביותר הוא הרבע שעה האחרונה בחלון.",
    "5m": "כל נר = חמש דקות. הנר הימני ביותר הוא חמש הדקות האחרונות בחלון.",
    "1m": "כל נר = דקה. הנר הימני ביותר הוא הדקה האחרונה בחלון.",
}

_PATTERN_HE: dict[str, str] = {
    "head_and_shoulders": "ראש וכתפיים (תבנית היפוך פוטנציאלית)",
    "bull_flag": "דגל שורי (המשך עליה פוטנציאלי)",
}


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except (TypeError, ValueError):
        return None


def _last_numeric(seq: list[Any] | None) -> tuple[int, float] | None:
    if not seq:
        return None
    for i in range(len(seq) - 1, -1, -1):
        v = _to_float(seq[i])
        if v is not None:
            return i, v
    return None


def _prev_numeric(seq: list[Any] | None, before_idx: int) -> float | None:
    if not seq or before_idx <= 0:
        return None
    for i in range(min(before_idx - 1, len(seq) - 2), -1, -1):
        v = _to_float(seq[i])
        if v is not None:
            return v
    return None


def _last_dual_aligned(
    a: list[Any] | None, b: list[Any] | None
) -> tuple[int, float, float] | None:
    """Last index where both series have numeric values (same bar)."""
    if not a or not b or len(a) != len(b):
        return None
    for i in range(len(a) - 1, -1, -1):
        va, vb = _to_float(a[i]), _to_float(b[i])
        if va is not None and vb is not None:
            return i, va, vb
    return None


def _prev_dual_aligned(
    a: list[Any] | None, b: list[Any] | None, before_idx: int
) -> tuple[float, float] | None:
    if not a or not b or before_idx <= 0:
        return None
    for j in range(before_idx - 1, -1, -1):
        va, vb = _to_float(a[j]), _to_float(b[j])
        if va is not None and vb is not None:
            return va, vb
    return None


def _fib_bracket(close: float, fib: dict[str, Any] | None) -> str | None:
    if not fib or close <= 0:
        return None
    levels = fib.get("levels")
    if not isinstance(levels, dict) or not levels:
        return None
    priced: list[tuple[str, float]] = []
    for k, v in levels.items():
        pv = _to_float(v)
        if pv is not None:
            priced.append((str(k), pv))
    if len(priced) < 2:
        return None
    priced.sort(key=lambda t: t[1])
    lo_p = priced[0][1]
    hi_p = priced[-1][1]
    if close < lo_p:
        return f"הסגירה האחרונה ({close:.2f}) נמוכה מכל רמות פיבונאצ'י המחושבות מהנדנדה בחלון — מתחת לטווח הרטרייסמנט."
    if close > hi_p:
        return f"הסגירה האחרונה ({close:.2f}) גבוהה מכל רמות פיבונאצ'י בחלון — מעל טווח הרטרייסמנט."
    for j in range(len(priced) - 1):
        a, pa = priced[j]
        b, pb = priced[j + 1]
        if pa <= close <= pb:
            return (
                f"מחיר הסגירה האחרון ({close:.2f}) נמצא **בין** רמת פיב `{a}` ({pa:.2f}) ל־`{b}` ({pb:.2f}) "
                f"— כלומר ביחס לנדנדה שזוהתה בחלון, המחיר \"יושב\" בתוך מסלול התיקון הסטנדרטי."
            )
    return None


def build_ohlcv_regime_lines(
    candles: list[dict[str, Any]],
    close: float,
    ind: dict[str, list[Any]],
) -> list[str]:
    """
    Educational synthesis: where price sits in the window's range vs momentum —
    explicitly NOT a forecast or advice.
    """
    n = len(candles)
    out: list[str] = []
    out.append(
        "**חשוב לדעת:** מה שבא בהמשך **לא** אומר אם כדאי לקנות או למכור, ולא חוזה עתיד עסקי של החברה."
    )
    out.append(
        "המטרה פה אחת: לעזור לך להבין **איפה נמצא המחיר בתוך הטווח שמוצג בגרף** — כלומר גבוה, נמוך או באמצע ביחס לשיא ולשפל של אותו חלון."
    )

    if n < 8:
        out.append("החלון כאן קצר מדי כדי לדבר על «שלב» ברור בתנועה — נסה טווח זמן ארוך יותר או יותר נרות בגרף.")
        return out

    lb = min(60, max(10, n - 1))
    win = candles[-lb:]
    hh_list: list[float] = []
    ll_list: list[float] = []
    for c in win:
        hh = _to_float(c.get("high"))
        ll = _to_float(c.get("low"))
        if hh is not None and ll is not None:
            hh_list.append(hh)
            ll_list.append(ll)
    if not hh_list:
        return out
    hi_w, lo_w = max(hh_list), min(ll_list)
    span = hi_w - lo_w
    if span <= 1e-12:
        out.append("בטווח שנבחר כמעט אין תנודה במחיר — קשה לדבר על מגמה או שלב בתוך הגרף.")
        return out

    pct = (close - lo_w) / span
    close_start = _to_float(candles[n - lb].get("close"))
    ret_lb = ((close / close_start) - 1.0) * 100.0 if close_start and close_start > 0 else None

    out.append(
        f"ב־**{lb}** הנרות האחרונים: השפל בחלון **{lo_w:.2f}**, השיא **{hi_w:.2f}**. "
        f"הסגירה האחרונה (**{close:.2f}**) יושבת בערך ב־**{pct * 100:.0f}%** של המרחק בין השפל לשיא — "
        "זה אומר **כמה גבוה או נמוך המחיר ביחס לטווח הזה**, לא מה יקרה לעסק בעוד חמש שנים."
    )
    if ret_lb is not None:
        out.append(
            f"תשואה **משוערת** על אותם {lb} נרות, מסגירה לסגירה מתחילת החלון ועד היום: **{ret_lb:+.1f}%**."
        )

    rsi_t = _last_numeric(ind.get("rsi14"))
    rsi_last = rsi_t[1] if rsi_t else None
    rsi_start: float | None = None
    rsi_series = ind.get("rsi14") or []
    if len(rsi_series) > n - lb:
        rsi_start = _to_float(rsi_series[n - lb])

    macd_pair = _last_dual_aligned(ind.get("macd"), ind.get("macd_signal"))
    macd_bull = bool(macd_pair and macd_pair[1] > macd_pair[2])

    vw_t = _last_numeric(ind.get("vwap"))
    vwap_above: bool | None = None
    if vw_t is not None:
        _, vv = vw_t
        if vv and vv > 0:
            vwap_above = close > vv

    bearish_div = False
    bullish_div = False
    if (
        ret_lb is not None
        and rsi_last is not None
        and rsi_start is not None
        and close_start is not None
        and close_start > 0
    ):
        if close > close_start * 1.02 and rsi_last < rsi_start - 4:
            bearish_div = True
        if close < close_start * 0.98 and rsi_last > rsi_start + 4:
            bullish_div = True

    story: str | None = None
    if bearish_div:
        out.append(
            "**פער (דיוורג׳נס פשוט):** המחיר עלה בחלון, אבל ה־RSI **ירד**. בניתוח טכני לפעמים מפרשים את זה כאות "
            "ש**המומנטום לא מחזק את העליה**. זה **לא** אומר שחייב להיות היפוך — רק שיש **אי־התאמה** בין מחיר למומנטום ששווה לשים לב אליה."
        )

    if bullish_div:
        out.append(
            "**פער בכיוון ההפוך:** המחיר ירד בחלון, אבל ה־RSI **עלה**. לפעמים מפרשים את זה כסימן שהלחץ השלילי **מתמתן** — "
            "עדיין מדובר בהנחה טכנית בלבד, לא בוודאות."
        )

    if (
        pct >= 0.82
        and ret_lb is not None
        and ret_lb > 6
        and rsi_last is not None
        and rsi_last >= 62
        and macd_bull
    ):
        story = (
            "**איך לקרוא את זה (רק מהגרף):** יש כאן מגמה חיובית **מתקדמת** בחלון — המחיר קרוב לשיא הטווח, "
            "התשואה על הנרות האלה חיובית בבירור, ה־RSI גבוה וה־MACD עדיין **שורי** (מעל קו האות). "
            "**בקצרה:** חלק ניכר מהעליה **כבר נספג במחיר** בטווח הזה. לכן לעיתים מדברים על שלב שבו **עולה הסיכון לתיקון קטן או לדשדוש** — "
            "בלי לומר «אין עתיד» או «העליה נגמרה»; רק שהתנועה **נראית צפופה יחסית** ולפעמים מחפשת «נשימה»."
        )
    elif (
        pct >= 0.78
        and ret_lb is not None
        and ret_lb > 5
        and macd_bull
        and (rsi_last is None or rsi_last < 58)
    ):
        story = (
            "**איך לקרוא את זה:** המחיר בחלק העליון של הטווח, אבל ה־RSI **לא** בקיצון. "
            "לפעמים זה מתאר מגמה שעדיין **לא נראית «רותחת»** באינדיקטור, או עליה עם **פחות לחץ מומנטום קיצוני** — תלוי גם בנפח ובהקשר."
        )
    elif (
        pct <= 0.18
        and ret_lb is not None
        and ret_lb < -6
        and rsi_last is not None
        and rsi_last <= 38
        and not macd_bull
    ):
        story = (
            "**איך לקרוא את זה:** ירידה ברורה בחלון, המחיר ליד **שפל הטווח**, RSI נמוך וה־MACD דובי. "
            "**בקצרה:** מבחינת מומנטום, **חלק גדול מלחץ המכירות כבר משוקע במחיר** בטווח הזה. "
            "זה **לא** אומר שהחברה «אבודה»; זה אומר ש**בגרף רואים שלב חלש**, ולפעמים ממנו יוצאות התאוששויות — **ולפעמים לא**."
        )
    elif pct <= 0.22 and macd_bull:
        story = (
            "**איך לקרוא את זה:** המחיר בתחתית הטווח, אבל ה־MACD כבר **שורי**. חלק מהסוחרים רואים בזה רמז אפשרי להיפוך או לרצף חדש. "
            "זו **השערה טכנית בלבד** — חשוב לשלב חדשות, נפח ונתונים עסקיים."
        )
    elif abs(pct - 0.5) <= 0.2 and (rsi_last is None or (35 <= rsi_last <= 65)):
        story = (
            "**איך לקרוא את זה:** המחיר באמצע הטווח, בלי קיצוני RSI בולטים — **תמונה מעורבת**. "
            "הגרף **לא נותן כאן תשובה חד־משמעית** לשאלה אם יש «עתיד»; הוא רק אומר שבחלון הזה **אין סיפור של קיצון ברור**."
        )
    else:
        story = (
            "**איך לקרוא את זה:** השילוב של מיקום בטווח, תשואה על החלון, RSI ו־MACD **לא חד־משמעי** — וזה בסדר גמור; "
            "רוב הזמן השוק **לא** נמצא בקיצון. כדי לחשוב על **מה יקרה הלאה** צריך טווח ארוך יותר, הבנת העסק וסיכון אישי, לא רק מסך אחד."
        )

    if story:
        out.append(story)

    if vwap_above is True and pct >= 0.75:
        out.append(
            "**יחד עם ה־VWAP:** הסגירה מעל ה־VWAP **ובמקביל** המחיר בחלק העליון של הטווח — "
            "לעיתים שני הדברים מחזקים יחד את הרושם ש**הקונים דומיננטיים בטווח**, אבל גם ש**הריצה כבר ארוכה יחסית**."
        )
    elif vwap_above is False and pct <= 0.35:
        out.append(
            "**חיבור ל־VWAP:** מתחת ל־VWAP ובחלק התחתון של הטווח — לעיתים נקרא שלב **חולשה יחסית** ביחס לממוצע המשוקלל נפח."
        )

    out.append(
        "**לסיכום:** שאלות כמו «אחרי העליה או לפני?» — הגרף נותן **רק** מסגרת של מומנטום ומיקום בטווח; "
        "**לא** תשובה אם המניה «תעלה שוב». זה בדיוק למה משלבים ניתוח נוסף מעבר לגרף."
    )
    return out


def build_ohlcv_snapshot_lines(
    symbol: str,
    timeframe: str,
    candles: list[dict[str, Any]],
    indicators: dict[str, list[Any]] | None,
    patterns: list[dict[str, Any]] | None,
    fibonacci: dict[str, Any] | None = None,
) -> list[str]:
    """Hebrew bullet lines describing the last bar and indicators for this symbol."""
    if not candles:
        return []
    ind = indicators or {}
    n = len(candles)
    last = candles[-1]
    o = _to_float(last.get("open"))
    h = _to_float(last.get("high"))
    l_ = _to_float(last.get("low"))
    c = _to_float(last.get("close"))
    if c is None or o is None or h is None or l_ is None:
        return [f"**{symbol}** — חסרים שדות OHLC בנר האחרון; לא ניתן לפרש."]

    lines: list[str] = []
    sym_bold = f"**{symbol}**"
    tf_note = _TF_CONTEXT.get(timeframe, f"מסגרת `{timeframe}` — כל נר הוא יחידת זמן אחת בחלון.")
    lines.append(f"{sym_bold} · {tf_note} סה״כ **{n}** נרות בגרף.")

    bull = c >= o
    direction = "נר **ירוק** (סגירה מעל פתיחה)" if bull else "נר **אדום** (סגירה מתחת לפתיחה)"
    move = abs(c - o)
    rng = h - l_
    lines.append(f"הנר הימני ביותר: {direction}, סגירה **{c:.2f}**, טווח יום/נר **{rng:.2f}** (גבוה–נמוך).")

    if rng > 1e-9:
        body_ratio = move / rng
        upper = h - max(o, c)
        lower = min(o, c) - l_
        if body_ratio >= 0.65:
            lines.append("הגוף ארוך ביחס לצללים — הכיוון בתוך הנר חד יחסית (פחות ספק בתוך אותה תקופה).")
        elif body_ratio <= 0.2:
            lines.append("גוף קצר מאוד מול הצללים — דחיפות דו־כיוונית או \"עצירה\" לפני המשך מגמה.")
        if upper > lower * 1.4 and upper > move:
            lines.append("צל עליון בולט — בזמן הנר היה לחץ מכירה שדחף את המחיר למטה מהשיא.")
        if lower > upper * 1.4 and lower > move:
            lines.append("צל תחתון בולט — היה קנייה שדחפה את המחיר מעלה מהשפל.")

    rsi_t = _last_numeric(ind.get("rsi14"))
    if rsi_t:
        rsi_i, rsi_v = rsi_t
        if rsi_i < n - 1:
            lines.append(
                f"**RSI**: המספר הבא מגיע מנר **{rsi_i + 1}** מתוך {n} — בנר הימני ביותר אין עדיין RSI חשוב."
            )
        if rsi_v >= 70:
            lines.append(
                f"**RSI(14)** בסוף החלון: **{rsi_v:.1f}** — מעל קו 70, אזור שמפרשים כלחץ קנייה חזק (לא אומר שחייב לרדת מיד)."
            )
        elif rsi_v <= 30:
            lines.append(
                f"**RSI(14)** בסוף החלון: **{rsi_v:.1f}** — מתחת ל־30, אזור שמפרשים כלחץ מכירה חזק (לא אומר שחייב לעלות מיד)."
            )
        else:
            lines.append(
                f"**RSI(14)** בסוף החלון: **{rsi_v:.1f}** — בין 30 ל־70, כלומר לפי הכלל הפשוט אין \"קיצון\" מומנטום ביחס לקווים על הגרף."
            )

    macd_line = ind.get("macd")
    macd_sig = ind.get("macd_signal")
    macd_hist = ind.get("macd_histogram") or ind.get("histogram")
    macd_pair = _last_dual_aligned(macd_line, macd_sig)
    if macd_pair:
        bar_i, m_v, s_v = macd_pair
        if bar_i < n - 1:
            lines.append(
                f"**MACD**: הקריאה הבאה מתייחסת לנר **{bar_i + 1}** מתוך {n} — לא בהכרח לנר הימני ביותר."
            )
        spread = m_v - s_v
        hist_word = "חיובי" if spread > 0 else "שלילי" if spread < 0 else "באפס (אין פער)"
        lines.append(
            f"**MACD** ({m_v:.4f}) מול **אות** ({s_v:.4f}) על **אותו נר** (אינדקס {bar_i + 1} בחלון) — "
            f"פער {spread:+.4f}, כלומר היסטוגרם **{hist_word}** בנקודה הזו על הגרף."
        )
        prev_ms = _prev_dual_aligned(macd_line, macd_sig, bar_i)
        if prev_ms:
            prev_m, prev_s = prev_ms
            was_below = prev_m < prev_s
            now_above = m_v > s_v
            if was_below and now_above:
                lines.append("לעומת הנר הקודם שבו שני הקווים מחושבים: **חצייה שורית** (MACD עבר מעל האות).")
            elif not was_below and not now_above:
                lines.append("לעומת הנר הקודם שבו שני הקווים מחושבים: **חצייה דובית** (MACD ירד מתחת לאות).")
            else:
                lines.append("יחס MACD מול האות **נשאר באותו צד** כמו בנר הקודם — אין חצייה חדשה, רק המשך או הצטמצמות של הפער.")

    if macd_hist:
        hi_t = _last_numeric(macd_hist)
        if hi_t:
            hi_idx, hv = hi_t
            prev_h = _prev_numeric(macd_hist, hi_idx)
            if prev_h is not None and hv != prev_h:
                if abs(hv) > abs(prev_h):
                    lines.append("עמודות ה־MACD (היסטוגרם) **מתארכות** — עוצמת המומנטום גדלה בכיוון הנוכחי.")
                else:
                    lines.append("עמודות ה־MACD **מתקצרות** — עוצמת המומנטום מתמתנת ביחס לנר הקודם.")

    vw_t = _last_numeric(ind.get("vwap"))
    if vw_t is not None and c is not None:
        _, vwap_v = vw_t
        diff_pct = (c - vwap_v) / vwap_v * 100.0 if vwap_v else 0.0
        if abs(diff_pct) < 0.05:
            lines.append(
                f"**VWAP** בסוף החלון ({vwap_v:.2f}) כמעט זהה לסגירה — המחיר \"יושב\" על מחיר ממוצע משוקלל נפח בתקופה."
            )
        elif c > vwap_v:
            lines.append(
                f"הסגירה **מעל** ה־VWAP ({vwap_v:.2f}), בערך **{diff_pct:+.2f}%** — ביחס למודל VWAP בחלון, לחץ יחסי של קונים."
            )
        else:
            lines.append(
                f"הסגירה **מתחת** ל־VWAP ({vwap_v:.2f}), בערך **{diff_pct:+.2f}%** — ביחס למודל VWAP בחלון, לחץ יחסי של מוכרים."
            )

    ten_kij = _last_dual_aligned(ind.get("ichimoku_tenkan"), ind.get("ichimoku_kijun"))
    if ten_kij:
        _, tv, kv = ten_kij
        if tv > kv:
            lines.append(
                f"**איצ׳ימוקו**: טנקן ({tv:.2f}) מעל קיג׳ון ({kv:.2f}) בנר האחרון — פרשנות קלאסית: מומנטום קצר־טווח חיובי יחסית."
            )
        elif tv < kv:
            lines.append(
                f"**איצ׳ימוקו**: טנקן ({tv:.2f}) מתחת לקיג׳ון ({kv:.2f}) — מומנטום קצר־טווח שלילי יחסית."
            )
        else:
            lines.append(f"**איצ׳ימוקו**: טנקן וקיג׳ון כמעט שווים ({tv:.2f}) — שיווי משקל בין קצר לבינוני בחלון.")

    if patterns:
        for p in patterns:
            raw_name = str(p.get("name", ""))
            label = _PATTERN_HE.get(raw_name, raw_name.replace("_", " "))
            s = int(p.get("start_index", 0))
            e = int(p.get("end_index", 0))
            conf = _to_float(p.get("confidence"))
            tail = ""
            if conf is not None:
                tail = f" (ביטחון אלגוריתמי ~{conf * 100:.0f}%)"
            at_right = e >= n - 1
            pos = f"נרות {s + 1}–{e + 1} מתוך {n} בחלון"
            if at_right:
                pos += " — **התבנית נוגעת בקצה הימני של הגרף** (רלוונטי למה שאתה רואה עכשיו)."
            lines.append(f"זוהתה תבנית **{label}**; {pos}.{tail}")

    fib_line = _fib_bracket(c, fibonacci)
    if fib_line:
        lines.append(fib_line)

    return lines


def render_ohlcv_snapshot_narrative(
    symbol: str,
    timeframe: str,
    candles: list[dict[str, Any]],
    indicators: dict[str, list[Any]] | None,
    patterns: list[dict[str, Any]] | None,
    fibonacci: dict[str, Any] | None = None,
) -> None:
    """Show practical interpretation for the OHLCV figure above."""
    lines = build_ohlcv_snapshot_lines(symbol, timeframe, candles, indicators, patterns, fibonacci)
    if not lines:
        return
    ind = indicators or {}
    last_c = _to_float((candles[-1] or {}).get("close"))
    regime: list[str] = []
    if last_c is not None:
        regime = build_ohlcv_regime_lines(candles, last_c, ind)

    st.markdown("#### בתכלס — מה הגרף הזה אומר עכשיו על המניה")
    st.caption("לפי הנר הימני ביותר והאינדיקטורים שמחושבים אצלך בחלון — מספרים קונקרטיים מהנתונים.")
    st.markdown("\n".join(f"- {line}" for line in lines))
    if regime:
        st.markdown("#### «עתיד», עליות ושלב בתנועה — מה **באמת** אפשר להסיק מהגרף")
        st.caption(
            "פרשנות חינוכית: איפה המחיר על **ציר התנועה בחלון** — לא חיזוי עסקי ולא המלצה."
        )
        st.markdown("\n".join(f"- {line}" for line in regime))
    st.caption(
        "זו קריאה אוטומטית של המערכת על הנתונים שבגרף — לא תחזית, לא המלצה, ולא ייעוץ השקעות."
    )


def build_portfolio_alpha_lines(
    alpha_data: dict[str, Any],
    snap: dict[str, Any],
    start_value: float,
    benchmark: str,
) -> list[str]:
    spy_dates = alpha_data.get("spy_dates") or []
    spy_vals = alpha_data.get("spy_normalized_values") or []
    if not spy_dates or not spy_vals or len(spy_vals) < 1:
        return []
    portfolio_ret = float(alpha_data.get("portfolio_total_return_pct") or 0.0)
    spy_ret = float(alpha_data.get("spy_total_return_pct") or 0.0)
    alpha_val = float(alpha_data.get("alpha_pct") or 0.0)
    current_equity = float(snap.get("total_equity", start_value))
    spy_end = float(spy_vals[-1])
    lines: list[str] = []
    lines.append(
        f"טווח הזמן על הציר: מ־**{spy_dates[0]}** עד **{spy_dates[-1]}** ({len(spy_dates)} נקודות) — "
        f"זה אותו חלון שבו חושבו אחוזי התשואה בכרטיסיות למעלה."
    )
    lines.append(
        f"הקו המנוקד (**{benchmark}**, כתום) מנורמל כך שהתחלה = **{start_value:,.0f}** דולר. "
        f"הנקודה **הימנית** על הקו הזה בערך **{spy_end:,.2f}** דולר — כלומר תשואה של **{spy_ret:+.2f}%** על המדד באותה תקופה."
    )
    lines.append(
        f"הקו הירוק הוא **רק שני קצוות**: התחלה ({start_value:,.0f}) וסוף (**{current_equity:,.2f}**) — "
        f"זה שווי התיק שלך **עכשיו** לעומת בסיס ההשוואה; תשואת התיק בחלון: **{portfolio_ret:+.2f}%**."
    )
    if alpha_val > 0:
        lines.append(
            f"בסוף החלון התיק **מוביל** את המדד ב־**{alpha_val:+.2f}%** (אלפא חיובית) — "
            "זה בדיוק המרווח שאתה רואה בין הנקודה הירוקה הימנית לבין גובה הקו הכתום באותו תאריך."
        )
    elif alpha_val < 0:
        lines.append(
            f"בסוף החלון התיק **מפגר** אחרי המדד ב־**{alpha_val:+.2f}%** — "
            "הנקודה הכתומה האחרונה גבוהה יותר מ־שווי התיק שלך ביחס לבסיס ההתחלה."
        )
    else:
        lines.append("בסוף החלון התיק והמדד כמעט **זהים** באחוזי התשואה — אלפא קרובה לאפס.")
    return lines


def render_portfolio_alpha_snapshot(
    alpha_data: dict[str, Any],
    snap: dict[str, Any],
    start_value: float,
    benchmark: str,
) -> None:
    lines = build_portfolio_alpha_lines(alpha_data, snap, start_value, benchmark)
    if not lines:
        return
    st.markdown("#### בתכלס — איך לקרוא את **הגרף הספציפי** של התיק שלך")
    st.caption("מספרים מה-API ומהנקודות שמוצגות — לא תיאוריה כללית.")
    st.markdown("\n".join(f"- {line}" for line in lines))
    st.caption(
        "זו קריאה אוטומטית על בסיס הנתונים שנטענו — לא ייעוץ השקעות."
    )


def build_blind_price_lines(chart_data: list[dict[str, Any]], price_snap: float) -> list[str]:
    if not chart_data or price_snap <= 0:
        return []
    prices: list[float] = []
    for d in chart_data:
        f = _to_float(d.get("price_factor"))
        if f is not None:
            prices.append(round(f * price_snap, 2))
    if len(prices) < 2:
        return []
    first_p, last_p = prices[0], prices[-1]
    hi, lo = max(prices), min(prices)
    lines: list[str] = []
    lines.append(
        f"יש **{len(prices)}** נקודות מחיר בגרף; כולן נגזרות ממכפיל יחסי על מחיר ה־snapshot (**{price_snap:.2f}** דולר)."
    )
    lines.append(
        f"הנקודה **השמאלית** (העבר הרחוק בחלון) בערך **{first_p:.2f}**; ה**ימנית** (הקרובה ל־snapshot) **{last_p:.2f}**."
    )
    chg = (last_p - first_p) / first_p * 100.0 if first_p else 0.0
    if last_p > first_p * 1.02:
        lines.append(f"במסגרת הגרף יש **עליה** גסה של כ־{chg:+.1f}% מהשמאל לימין — לפני שמסיקים, לשלב עם המדדים למעלה.")
    elif last_p < first_p * 0.98:
        lines.append(f"במסגרת הגרף יש **ירידה** גסה של כ־{chg:+.1f}% — שוב, רק הקשר של התרחיש.")
    else:
        lines.append("במסגרת הגרף המחיר **דשדש** סביב טווח צר יחסית — פחות מגמה ברורה בנקודות שמוצגות.")
    above = sum(1 for p in prices if p >= price_snap)
    lines.append(
        f"קו ה־snapshot (**{price_snap:.2f}**): **{above}** מתוך {len(prices)} נקודות מעליו או עליו, "
        f"**{len(prices) - above}** מתחתיו — כלומר איפה המחיר היה ביחס לרמת ההחלטה לאורך החלון."
    )
    lines.append(
        f"שיא בחלון: **{hi:.2f}**, שפל: **{lo:.2f}** — רואים כמה \"מרחק\" היה מהקצוות לעומת מחיר ה־snapshot."
    )
    return lines


def render_blind_price_snapshot(chart_data: list[dict[str, Any]], price_snap: float) -> None:
    lines = build_blind_price_lines(chart_data, price_snap)
    if not lines:
        return
    st.markdown("#### בתכלס — איך לקרוא את **הגרף של התרחיש** הזה")
    st.markdown("\n".join(f"- {line}" for line in lines))
    st.caption("הנתונים אנונימיים בכוונה; הפרשנות היא על הצורה והמספרים שמוצגים בלבד.")


def build_treasury_history_lines(values: list[float]) -> list[str]:
    if len(values) < 2:
        return []
    last = values[-1]
    first = values[0]
    n = len(values)
    lines: list[str] = []
    lines.append(
        f"הנקודה **הימנית ביותר** על הגרף = תשואת 10 שנים **העדכנית** בחלון: **{last:.3f}%**."
    )
    whole_change = last - first
    lines.append(
        f"בקצה **השמאלי** של אותו חלון התשואה הייתה **{first:.3f}%** — שינוי של **{whole_change:+.3f}** נקודות אחוז לאורך כל הטווח שמוצג."
    )
    tail = values[-21:] if len(values) >= 21 else values
    head = values[:21] if len(values) >= 21 else values
    avg_tail = sum(tail) / len(tail)
    avg_head = sum(head) / len(head)
    if len(values) >= 42:
        lines.append(
            f"ממוצע תשואה על **~20 התצפיות האחרונות**: **{avg_tail:.3f}%**; "
            f"על **~20 הראשונות** בחלון: **{avg_head:.3f}%** — "
            f"{'המגמה האחרונה חזקה יותר מבתחילת החלון' if avg_tail > avg_head else 'המגמה האחרונה חלשה יותר מבתחילת החלון' if avg_tail < avg_head else 'אין הפרש ממוצע משמעותי בין ראש לזנב החלון'}."
        )
    return lines


def render_treasury_history_snapshot(values: list[float]) -> None:
    lines = build_treasury_history_lines(values)
    if not lines:
        return
    st.markdown("#### בתכלס — מה קורה **בגרף התשואות** שמעליך")
    st.markdown("\n".join(f"- {line}" for line in lines))
    st.caption("נתוני FRED לצורכי למידה; לא ייעוץ.")
