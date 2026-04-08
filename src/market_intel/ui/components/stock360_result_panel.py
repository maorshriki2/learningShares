"""Shared rendering for Stock 360 Final Verdict API payload (real ticker or blind CSV)."""

from __future__ import annotations

import math
from typing import Any

import streamlit as st

from market_intel.modules.analytics.fundamental_stress_fusion import apply_fundamental_stress_fusion
from market_intel.ui.components.research_story_panel import render_research_insights_he


def _fund_dict_for_stress_ui(result: dict[str, Any]) -> dict[str, Any]:
    """Merge API `inputs.fundamentals` with blind dashboard so stress fusion matches the table above."""
    inputs = result.get("inputs") or {}
    fund: dict[str, Any] = dict(inputs.get("fundamentals") or {})
    dash = result.get("blind_dashboard") or {}
    if isinstance(dash, dict):
        for k in (
            "altman_z",
            "piotroski_score",
            "forensic_flags",
            "roic_latest",
            "wacc",
            "margin_of_safety_pct",
        ):
            v = dash.get(k)
            if v is not None and (k not in fund or fund.get(k) is None):
                fund[k] = v
    return fund


def _ensure_fundamental_stress_on_verdict(result: dict[str, Any]) -> None:
    """
    Re-apply stress fusion in the UI if the connected API is older (omits fusion) or payload is partial.
    Safe no-op when `fundamental_stress_active` is already True.
    """
    verdict = result.get("verdict")
    if not isinstance(verdict, dict):
        return
    if verdict.get("fundamental_stress_active"):
        return
    fund = _fund_dict_for_stress_ui(result)
    if not fund:
        return
    apply_fundamental_stress_fusion(verdict, fund)


def _to_f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _fmt_usd(x: Any, digits: int = 2) -> str:
    v = _to_f(x)
    if v is None:
        return "—"
    return f"${v:,.{digits}f}"


def _fmt_pct01(x: Any, digits: int = 1) -> str:
    v = _to_f(x)
    if v is None:
        return "—"
    return f"{v*100:.{digits}f}%"


def _horizon_label(days: int | None, fallback: str) -> str:
    if days == 30:
        return "חודש (30d)"
    if days == 90:
        return "3 חודשים (90d)"
    if days == 180:
        return "6 חודשים (180d)"
    if days == 365:
        return "שנה (365d)"
    return fallback


def render_stock360_verdict_result(
    result: dict[str, Any],
    *,
    include_explain: bool = True,
    study_financials: dict[str, Any] | None = None,
    research_include_forensic: bool = True,
) -> None:
    if not result.get("ok"):
        st.error(result.get("message") or "Final Verdict failed.")
        st.json(result)
        return

    _ensure_fundamental_stress_on_verdict(result)
    verdict = result.get("verdict") or {}

    if verdict.get("fundamental_stress_active"):
        st.error(verdict.get("fundamental_stress_no_entry_he") or "מצוקה פיננסית חריפה — לא כהמלצת כניסה.")
        st.warning(verdict.get("fundamental_stress_trading_gate_he") or "")
        rs_top = (verdict.get("fundamental_stress_reasons_he") or [])[:5]
        if rs_top:
            st.markdown("**אותות שזוהו:**")
            for line in rs_top:
                st.markdown(f"- {line}")

    vcol1, vcol2, vcol3 = st.columns([1.2, 1.6, 2.2])
    vcol1.metric("מחיר נוכחי", _fmt_usd(verdict.get("current_price")))
    dir_raw = str(verdict.get("forecast_direction") or "")
    dir_he = "לא זמין"
    if dir_raw == "up":
        dir_he = "כיוון חיובי (Up)"
    elif dir_raw == "down_or_flat":
        dir_he = "שטוח/שלילי (Down/Flat)"
    if verdict.get("fundamental_stress_active"):
        dir_he = f"{dir_he} — **לא לכניסה** (סיכון)"
    vcol2.metric("כיוון צפוי (מודל)", dir_he)
    vcol3.metric("מחיר כניסה הכרחי (מודל)", _fmt_usd(verdict.get("required_entry_price")))
    if verdict.get("fundamental_stress_active"):
        st.warning(
            verdict.get("fundamental_stress_note_he")
            or "הופעלה תאימות פנדמנטלית: כיוון ההמלצה הותאם לעומת המודל הטכני בלבד."
        )
        rs = verdict.get("fundamental_stress_reasons_he") or []
        if len(rs) > 5:
            with st.expander("כל סיבות התאימות הפנדמנטלית", expanded=False):
                for line in rs:
                    st.markdown(f"- {line}")
        raw_dir = verdict.get("forecast_direction_ml_raw")
        cur_dir = verdict.get("forecast_direction")
        if raw_dir and cur_dir and raw_dir != cur_dir:
            st.caption(
                f"מודל ML בלבד הצביע על **{raw_dir}**; אחרי שילוב איכות/MOS/פורנזיקה — **{cur_dir}**."
            )

    fund_view = _fund_dict_for_stress_ui(result)
    if fund_view:
        st.divider()
        render_research_insights_he(
            dash=fund_view,
            verdict=verdict if isinstance(verdict, dict) else None,
            study_financials=study_financials,
            include_forensic_duplicates=research_include_forensic,
        )

    st.caption(
        "התחזית מבוססת על מודל סטטיסטי חינוכי (לא המלצת השקעה). "
        "הסתברויות מניחות התפלגות נורמלית על תשואות לוגריתמיות; בין אופקים אין חובה לייחס מונוטוניות."
    )
    _entry_notes = verdict.get("required_entry_notes") or []
    if verdict.get("required_entry_price") is None and isinstance(_entry_notes, list) and _entry_notes:
        with st.expander("למה אין מחיר כניסה מוצג?", expanded=False):
            for n in _entry_notes:
                st.markdown(f"- {n}")

    targets = verdict.get("targets") or {}
    probs = verdict.get("probabilities") or {}
    dist = verdict.get("distribution") or {}

    st.markdown("### יעדי מחיר (Price Targets)")
    rows_t: list[dict[str, object]] = []
    if isinstance(targets, dict):
        for key, obj in targets.items():
            if not isinstance(obj, dict):
                continue
            hd = _to_f(obj.get("horizon_days"))
            days = int(hd) if hd is not None else None
            label = _horizon_label(days, str(key))
            cur = _to_f(obj.get("current_price"))
            tgt = _to_f(obj.get("price_target"))
            ret = ((tgt / cur) - 1.0) if (cur is not None and tgt is not None and cur > 0) else None
            rows_t.append(
                {
                    "אופק": label,
                    "מחיר נוכחי": _fmt_usd(cur),
                    "מחיר מטרה": _fmt_usd(tgt),
                    "תשואה חזויה": _fmt_pct01(ret, 1) if ret is not None else "—",
                }
            )
    if rows_t:
        st.dataframe(rows_t, use_container_width=True)
    else:
        st.info("אין יעדים זמינים מהשרת. פתח את Explain למטה כדי לראות למה (לרוב: insufficient_samples).")

    st.markdown("### הסתברויות (Events)")
    rows_p: list[dict[str, object]] = []
    if isinstance(probs, dict):
        for key, obj in probs.items():
            if not isinstance(obj, dict):
                continue
            days = None
            if isinstance(key, str) and key.endswith("d"):
                try:
                    days = int(key[:-1])
                except ValueError:
                    days = None
            label = _horizon_label(days, str(key))
            rows_p.append(
                {
                    "אופק": label,
                    "P(תשואה>0)": _fmt_pct01(obj.get("p_return_positive"), 1),
                    "P(תשואה>10%)": _fmt_pct01(obj.get("p_return_above_10pct"), 1),
                    "P(תשואה<-10%)": _fmt_pct01(obj.get("p_return_below_-10pct"), 1),
                }
            )
    if rows_p:
        st.dataframe(rows_p, use_container_width=True)
    else:
        st.info("אין הסתברויות זמינות מהשרת.")

    st.markdown("### טווחים (Distribution)")
    rows_d: list[dict[str, object]] = []
    if isinstance(dist, dict):
        for key, obj in dist.items():
            if not isinstance(obj, dict):
                continue
            days = None
            if isinstance(key, str) and key.endswith("d"):
                try:
                    days = int(key[:-1])
                except ValueError:
                    days = None
            label = _horizon_label(days, str(key))
            rows_d.append(
                {
                    "אופק": label,
                    "P10": _fmt_usd(obj.get("p10")),
                    "P50": _fmt_usd(obj.get("p50")),
                    "P90": _fmt_usd(obj.get("p90")),
                    "μ תשואה": _fmt_pct01(obj.get("mu_ret"), 2),
                    "σ תשואה": _fmt_pct01(obj.get("sigma_ret"), 2),
                }
            )
    if rows_d:
        st.dataframe(rows_d, use_container_width=True)
    else:
        st.info("אין טווחים זמינים מהשרת.")

    st.markdown("### סיכונים מרכזיים (Risk Register)")
    risks = verdict.get("risks") or []
    if isinstance(risks, list) and risks:
        for r in risks:
            if not isinstance(r, dict):
                continue
            sev = str(r.get("severity") or "info").lower()
            title = str(r.get("risk") or "Risk")
            detail = r.get("value") if r.get("value") is not None else r.get("count") or r.get("trigger")
            if sev == "high":
                st.error(f"**{title}**")
            elif sev == "medium":
                st.warning(f"**{title}**")
            else:
                st.info(f"**{title}**")
            if detail is not None:
                st.caption(str(detail))
    else:
        st.success("לא הופעלו סיכונים חזקים לפי כללי המודל (לא אומר שאין סיכון).")

    notes = verdict.get("required_entry_notes") or []
    if notes:
        with st.expander("איך נקבע 'מחיר כניסה הכרחי' (Explain)", expanded=False):
            for n in notes:
                st.markdown(f"- {n}")

    with st.expander("Explain — inputs (raw)", expanded=False):
        st.caption("פירוט inputs שהשרת השתמש בהם לחישוב (למתקדמים).")
        inputs = result.get("inputs") or {}
        if isinstance(inputs, dict):
            st.dataframe(
                [
                    {
                        "section": k,
                        "keys": ", ".join(sorted((v or {}).keys())) if isinstance(v, dict) else type(v).__name__,
                    }
                    for k, v in inputs.items()
                ],
                use_container_width=True,
            )
        else:
            st.write("—")

    with st.expander("Explain — model metadata", expanded=False):
        st.caption("פרטי מודל: סוג, הנחות, אופקים, הערות אמינות.")
        model = result.get("model") or {}
        if isinstance(model, dict):
            flat = []
            for k, v in model.items():
                if isinstance(v, (dict, list)):
                    continue
                flat.append({"key": k, "value": v})
            if flat:
                st.dataframe(flat, use_container_width=True)
            mnotes = model.get("notes")
            if isinstance(mnotes, list) and mnotes:
                st.markdown("**Notes**")
                for n in mnotes:
                    st.markdown(f"- {n}")
            missing = model.get("missing_features")
            if isinstance(missing, dict) and missing:
                st.markdown("**Missing features**")
                st.dataframe(
                    [{"feature": k, "missing": bool(v)} for k, v in missing.items()],
                    use_container_width=True,
                )
        else:
            st.write("—")

    if include_explain:
        with st.expander("Explain — פרטי רגרסיה לכל אופק (למתקדמים)", expanded=False):
            st.caption("מקדמים, וקטור פיצ'רים אחרון, ותוצאות backtest בסיסי.")
            ex = result.get("explain") or {}
            if not isinstance(ex, dict) or not ex:
                st.info("אין explain payload.")
            else:
                for hk, hv in ex.items():
                    st.markdown(f"#### Horizon {hk}")
                    if isinstance(hv, dict) and hv.get("ok") is False:
                        st.warning(f"לא נבנה מודל לאופק הזה: {hv.get('reason')} (n={hv.get('n')})")
                        continue
                    if not isinstance(hv, dict):
                        st.write(hv)
                        continue
                    bt = hv.get("walk_forward_backtest") if isinstance(hv.get("walk_forward_backtest"), dict) else None
                    if bt:
                        st.dataframe([bt], use_container_width=True)
                    coef = hv.get("coef") if isinstance(hv.get("coef"), dict) else {}
                    xlast = hv.get("x_last") if isinstance(hv.get("x_last"), dict) else {}
                    if coef:
                        items = [{"feature": k, "coef": float(v)} for k, v in coef.items() if _to_f(v) is not None]
                        items.sort(key=lambda r: abs(r["coef"]), reverse=True)
                        st.markdown("**Top coefficients (abs)**")
                        st.dataframe(items[:12], use_container_width=True)
                    if xlast:
                        xl = [{"feature": k, "value": float(v)} for k, v in xlast.items() if _to_f(v) is not None]
                        st.markdown("**Latest feature vector**")
                        st.dataframe(xl, use_container_width=True)

    st.caption("Educational only — not investment advice.")
