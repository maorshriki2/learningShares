from __future__ import annotations

import io
import json
from typing import Any

import pandas as pd


FIN_KEYS = (
    "revenue_b",
    "net_income_b",
    "total_assets_b",
    "total_liabilities_b",
    "operating_cashflow_b",
    "long_term_debt_b",
    "book_value_per_share",
    "pe_ratio",
    "debt_to_equity",
)

OPTIONAL_REVEAL_KEYS = ("price_one_year_later", "reveal_name", "outcome_label")


def _clean_scalar(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v


def blind_study_to_csv_bytes(study: dict[str, Any]) -> bytes:
    """Serialize a blind payload (API /get_blind shape) to a single-row CSV."""
    fin = study.get("financials_summary") or {}
    row: dict[str, Any] = {
        "mi_blind_export_version": 1,
        "year": _clean_scalar(study.get("year")),
        "sector": _clean_scalar(study.get("sector")),
        "price_at_snapshot": _clean_scalar(study.get("price_at_snapshot")),
        "piotroski_score": _clean_scalar(study.get("piotroski_score")),
        "altman_z": _clean_scalar(study.get("altman_z")),
        "altman_zone": _clean_scalar(study.get("altman_zone")),
        "price_chart_json": json.dumps(study.get("price_chart_data") or [], ensure_ascii=False),
        "source_study_id": _clean_scalar(study.get("id")),
    }
    for k in FIN_KEYS:
        row[k] = _clean_scalar(fin.get(k))
    df = pd.DataFrame([row])
    return df.to_csv(index=False).encode("utf-8-sig")


def _num(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return float(v)


def _row_to_study(row: dict[str, Any]) -> dict[str, Any]:
    fin: dict[str, Any] = {}
    for k in FIN_KEYS:
        if k not in row:
            continue
        v = row[k]
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        fin[k] = float(v) if isinstance(v, (int, float)) else v

    raw_chart = row.get("price_chart_json")
    if raw_chart is None or (isinstance(raw_chart, float) and pd.isna(raw_chart)):
        chart: list[dict[str, Any]] = []
    elif isinstance(raw_chart, str):
        try:
            chart = json.loads(raw_chart.strip() or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError(f"שדה price_chart_json לא JSON תקין: {exc}") from exc
    else:
        chart = []

    y_raw = row.get("year")
    year = int(float(y_raw)) if y_raw is not None and pd.notna(y_raw) else 0

    pi_raw = row.get("piotroski_score")
    piotroski = int(float(pi_raw)) if pi_raw is not None and pd.notna(pi_raw) else None

    az = _num(row.get("altman_z"))
    px = _num(row.get("price_at_snapshot")) or 0.0

    study: dict[str, Any] = {
        "id": "csv_import",
        "codename": "anony",
        "year": year,
        "sector": str(row.get("sector") or "").strip() or "—",
        "price_at_snapshot": px,
        "financials_summary": fin,
        "piotroski_score": piotroski,
        "altman_z": az,
        "altman_zone": str(row.get("altman_zone") or "grey").strip() or "grey",
        "price_chart_data": chart,
    }

    for k in OPTIONAL_REVEAL_KEYS:
        if k in row and pd.notna(row.get(k)):
            if k == "price_one_year_later":
                study[k] = float(row[k])
            else:
                study[k] = str(row[k])

    return study


def blind_study_from_csv_bytes(raw: bytes) -> dict[str, Any]:
    df = pd.read_csv(io.BytesIO(raw))
    if df.empty:
        raise ValueError("הקובץ ריק.")
    row = df.iloc[0].to_dict()
    return _row_to_study(row)
