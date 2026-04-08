"""
Shared Stock 360 Final Verdict pipeline: same ML + entry/risk logic as the API router,
so blind/anonymous scenarios can reuse identical machinery.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from market_intel.modules.analytics.fundamental_stress_fusion import apply_fundamental_stress_fusion


def finite_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def linear_regression_fit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    ones = np.ones((X.shape[0], 1), dtype=float)
    A = np.concatenate([ones, X], axis=1)
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    intercept = float(beta[0])
    coef = beta[1:].astype(float)
    return coef, intercept


def walk_forward_backtest(
    X: np.ndarray, y: np.ndarray, *, min_train: int = 220, step: int = 5
) -> dict[str, float | int]:
    n = int(len(y))
    if n < min_train + 10:
        return {"ok": 0, "n_eval": 0, "mse": float("nan"), "dir_acc": float("nan")}
    preds: list[float] = []
    actual: list[float] = []
    for i in range(min_train, n, step):
        coef, intercept = linear_regression_fit(X[:i], y[:i])
        preds.append(float(intercept + float(np.dot(X[i], coef))))
        actual.append(float(y[i]))
    if not preds:
        return {"ok": 0, "n_eval": 0, "mse": float("nan"), "dir_acc": float("nan")}
    p = np.asarray(preds, dtype=float)
    a = np.asarray(actual, dtype=float)
    mse = float(np.mean((p - a) ** 2))
    dir_acc = float(np.mean((p > 0) == (a > 0)))
    return {"ok": 1, "n_eval": int(len(p)), "mse": mse, "dir_acc": dir_acc}


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"].astype(float)
    feats = pd.DataFrame(index=df.index)
    feats["ret_1d"] = close.pct_change()
    feats["sma20"] = close.rolling(20).mean()
    feats["sma50"] = close.rolling(50).mean()
    feats["sma200"] = close.rolling(200).mean()
    feats["ema20"] = close.ewm(span=20, adjust=False).mean()
    feats["ema50"] = close.ewm(span=50, adjust=False).mean()
    feats["dist_sma20"] = (close / feats["sma20"]) - 1.0
    feats["dist_sma50"] = (close / feats["sma50"]) - 1.0
    feats["dist_sma200"] = (close / feats["sma200"]) - 1.0
    feats["dist_ema20"] = (close / feats["ema20"]) - 1.0
    feats["dist_ema50"] = (close / feats["ema50"]) - 1.0
    feats["vol20"] = feats["ret_1d"].rolling(20).std(ddof=0) * math.sqrt(252.0)
    feats["mom20"] = close.pct_change(20)
    feats["mom60"] = close.pct_change(60)
    return feats


def calendar_days_to_trading_bars(days: int) -> int:
    d = int(days)
    if d <= 1:
        return 1
    bars = int(round(d * (252.0 / 365.0)))
    return max(2, bars)


def compute_final_verdict_payload(
    *,
    sym: str,
    df: pd.DataFrame,
    fund: dict[str, Any],
    inst: dict[str, Any],
    horizons_cal: list[int],
    indicators: dict[str, Any],
    peers_payload: dict[str, Any] | None,
    include_explain: bool,
    current_price_override: float | None = None,
) -> dict[str, Any]:
    """
    Same outputs as GET /stock360/{symbol}/final-verdict (when ok=True).
    """
    if df.empty or "close" not in df:
        return {"ok": False, "symbol": sym, "message": "No price history available."}

    close = df["close"].astype(float)
    last_close = float(close.iloc[-1]) if len(close) else 0.0
    if current_price_override is not None and current_price_override > 0:
        current_price = float(current_price_override)
    elif last_close > 0:
        current_price = last_close
    else:
        pos = close[close > 1e-12]
        current_price = float(pos.iloc[-1]) if len(pos) > 0 else 0.0
    feats = build_features(df)
    horizons_map: list[dict[str, int]] = [
        {"calendar_days": int(hc), "trading_bars": calendar_days_to_trading_bars(int(hc))}
        for hc in horizons_cal
    ]
    diag: dict[str, Any] = {
        "bars_loaded": int(len(df)),
        "bars_required_for_features": 200,
        "close_last": current_price,
        "horizons_calendar_days": horizons_cal,
        "horizons_trading_bars": {str(m["calendar_days"]): m["trading_bars"] for m in horizons_map},
    }

    feature_cols = [
        "dist_sma20",
        "dist_sma50",
        "dist_sma200",
        "dist_ema20",
        "dist_ema50",
        "vol20",
        "mom20",
        "mom60",
    ]
    Xdf = feats[feature_cols].copy()
    roic = finite_float(fund.get("roic_latest"))
    mos = finite_float(fund.get("margin_of_safety_pct"))
    wacc = finite_float(fund.get("wacc"))
    Xdf["roic_latest"] = float(roic) if roic is not None else 0.0
    Xdf["mos_pct"] = float(mos) if mos is not None else 0.0
    Xdf["wacc"] = float(wacc) if wacc is not None else 0.0
    feature_cols_full = feature_cols + ["roic_latest", "mos_pct", "wacc"]

    forecasts: dict[str, Any] = {"targets": {}, "probabilities": {}, "distribution": {}, "explain": {}}

    for hm in horizons_map:
        h_cal = int(hm["calendar_days"])
        h = int(hm["trading_bars"])
        y = np.log(close.shift(-h) / close)
        joined = pd.concat([Xdf, y.rename("y")], axis=1)
        n_joined = int(len(joined))
        na_counts = joined.isna().sum().to_dict()
        data = joined.dropna()
        data = data.iloc[-750:]
        if len(data) < 120:
            forecasts["explain"][str(h_cal)] = {
                "ok": False,
                "reason": "insufficient_samples",
                "n": int(len(data)),
                "n_joined": n_joined,
                "calendar_days": h_cal,
                "trading_bars": h,
                "na_counts_top": dict(
                    sorted(((k, int(v)) for k, v in na_counts.items()), key=lambda kv: kv[1], reverse=True)[:8]
                ),
                "hint": "If n==0, likely not enough bars for SMA200/mom60 or provider returned short history.",
            }
            continue
        X = data[feature_cols_full].to_numpy(dtype=float)
        yv = data["y"].to_numpy(dtype=float)
        try:
            ql = float(np.quantile(yv, 0.01))
            qh = float(np.quantile(yv, 0.99))
            yv = np.clip(yv, ql, qh)
        except Exception:
            pass
        coef, intercept = linear_regression_fit(X, yv)
        resid = yv - (intercept + X.dot(coef))
        sigma = float(np.std(resid, ddof=0))
        backtest = walk_forward_backtest(X, yv)

        x_last = Xdf.iloc[-1][feature_cols_full].to_numpy(dtype=float)
        mu = float(intercept + float(np.dot(x_last, coef)))

        tgt = current_price * float(math.exp(mu))
        p10 = current_price * float(math.exp(mu + sigma * -1.2816))
        p50 = current_price * float(math.exp(mu))
        p90 = current_price * float(math.exp(mu + sigma * 1.2816))

        prob_up = norm_cdf(mu / sigma) if sigma > 1e-9 else (1.0 if mu > 0 else 0.0)
        ln_0p9 = math.log(0.9)
        ln_1p1 = math.log(1.1)
        prob_down_10 = norm_cdf((ln_0p9 - mu) / sigma) if sigma > 1e-9 else (1.0 if mu < ln_0p9 else 0.0)
        prob_above_10 = (
            1.0 - norm_cdf((ln_1p1 - mu) / sigma) if sigma > 1e-9 else (1.0 if mu > ln_1p1 else 0.0)
        )

        key = f"{h_cal}d"
        forecasts["targets"][key] = {
            "horizon_days": h_cal,
            "horizon_bars": h,
            "current_price": current_price,
            "price_target": tgt,
        }
        mu_ret = float(math.exp(mu) - 1.0)
        sigma_ret = float(sigma)
        forecasts["distribution"][key] = {
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "mu_ret": mu_ret,
            "sigma_ret": sigma_ret,
        }
        forecasts["probabilities"][key] = {
            "p_return_positive": prob_up,
            "p_return_below_-10pct": prob_down_10,
            "p_return_above_10pct": prob_above_10,
        }
        if include_explain:
            forecasts["explain"][key] = {
                "n_samples": int(len(data)),
                "n_joined": n_joined,
                "calendar_days": h_cal,
                "trading_bars": h,
                "walk_forward_backtest": backtest,
                "feature_cols": feature_cols_full,
                "coef": {feature_cols_full[i]: float(coef[i]) for i in range(len(feature_cols_full))},
                "intercept": float(intercept),
                "x_last": {feature_cols_full[i]: float(x_last[i]) for i in range(len(feature_cols_full))},
            }

    dcf = fund.get("dcf_base") if isinstance(fund.get("dcf_base"), dict) else {}
    intrinsic = finite_float(dcf.get("intrinsic_per_share"))
    vol_1y = finite_float(inst.get("volatility_1y"))

    required_entry = None
    entry_notes: list[str] = []
    if intrinsic is not None and math.isfinite(intrinsic):
        sane = (
            intrinsic > 0
            and current_price > 0
            and (0.02 * current_price) <= intrinsic <= (80.0 * current_price)
        )
        if not sane:
            entry_notes.append(
                "מחיר כניסה מבוסס DCF לא הוצג: intrinsic מה‑DCF לא סביר מול מחיר השוק (שגיאת מודל/נתונים)."
            )
        elif intrinsic <= current_price:
            entry_notes.append(
                "מחיר כניסה מבוסס DCF לא הוצג: לפי ה‑DCF המניה אינה בתמחור‑חסר (intrinsic ≤ מחיר שוק)."
            )
        else:
            mos_req = 0.15
            required_entry = intrinsic * (1.0 - mos_req)
            entry_notes.append(f"Require MOS≥{mos_req*100:.0f}% vs DCF intrinsic (entry≤intrinsic*(1-MOS)).")
    if vol_1y is not None and required_entry is not None and required_entry > 0:
        buf = min(0.20, max(0.0, (vol_1y - 0.25) * 0.5))
        required_entry = required_entry * (1.0 - buf)
        entry_notes.append(f"Volatility buffer applied (vol_1y={vol_1y:.2f} → extra discount {buf*100:.0f}%).")
    if required_entry is not None and (required_entry <= 0 or not math.isfinite(required_entry)):
        required_entry = None
        entry_notes.append("מחיר כניסה לא חוקי אחרי חישוב — הושמט.")

    risks: list[dict[str, object]] = []
    if vol_1y is not None and vol_1y >= 0.45:
        risks.append({"severity": "high", "risk": "High realized volatility (1Y)", "value": vol_1y})
    if mos is not None and mos < -15:
        risks.append({"severity": "medium", "risk": "Negative margin of safety", "value": mos})
    forensic_flags = fund.get("forensic_flags") or []
    high_forensic = [f for f in forensic_flags if isinstance(f, dict) and f.get("severity") == "high"]
    if high_forensic:
        risks.append({"severity": "high", "risk": "Forensic red flags", "count": len(high_forensic)})

    ml_up = any(
        (finite_float(v.get("mu_ret")) or 0.0) > 0
        for v in forecasts.get("distribution", {}).values()
        if isinstance(v, dict)
    )
    verdict = {
        "symbol": sym,
        "current_price": current_price,
        "forecast_direction": "up" if ml_up else "down_or_flat",
        "targets": forecasts["targets"],
        "probabilities": forecasts["probabilities"],
        "distribution": forecasts["distribution"],
        "required_entry_price": required_entry,
        "required_entry_notes": entry_notes,
        "risks": risks,
    }
    apply_fundamental_stress_fusion(verdict, fund)

    return {
        "ok": True,
        "symbol": sym,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "diagnostics": diag,
        "inputs": {
            "instrument_summary": inst,
            "indicators": indicators,
            "fundamentals": {
                "wacc": fund.get("wacc"),
                "roic_latest": fund.get("roic_latest"),
                "margin_of_safety_pct": fund.get("margin_of_safety_pct"),
                "altman_z": fund.get("altman_z"),
                "piotroski_score": fund.get("piotroski_score"),
                "dcf_base": fund.get("dcf_base"),
                "forensic_flags": fund.get("forensic_flags"),
            },
            "peers": peers_payload.get("explain") if isinstance(peers_payload, dict) else None,
        },
        "model": {
            "type": "per-horizon-linear-regression",
            "assumption": "Normal residuals for probabilities; educational.",
            "horizons_days": horizons_cal,
            "notes": [
                "Model is fit per-symbol on recent history (rolling samples).",
                "Backtest is a simple walk-forward sanity check, not a guarantee.",
                "Fundamentals features are constant placeholders when missing (roic/mos/wacc).",
                "Horizons are requested in calendar days and converted to approximate trading bars (252/365).",
                "If verdict shows fundamental_stress_active, short-horizon ML direction was fused with quality/MOS/forensics.",
            ],
            "missing_features": {
                "roic_latest_missing": roic is None,
                "mos_missing": mos is None,
                "wacc_missing": wacc is None,
            },
        },
        "explain": forecasts["explain"] if include_explain else {},
    }
