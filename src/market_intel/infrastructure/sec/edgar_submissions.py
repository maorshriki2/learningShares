from __future__ import annotations

from typing import Any


def filter_recent_filings(
    submissions_json: dict[str, Any],
    forms: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    forms_list = submissions_json.get("filings", {}).get("recent", {}).get("form", [])
    accession = submissions_json.get("filings", {}).get("recent", {}).get("accessionNumber", [])
    filing_date = submissions_json.get("filings", {}).get("recent", {}).get("filingDate", [])
    primary_doc = submissions_json.get("filings", {}).get("recent", {}).get("primaryDocument", [])
    out: list[dict[str, Any]] = []
    n = len(forms_list)
    for i in range(n):
        if forms_list[i] not in forms:
            continue
        out.append(
            {
                "form": forms_list[i],
                "accessionNumber": accession[i],
                "filingDate": filing_date[i],
                "primaryDocument": primary_doc[i] if i < len(primary_doc) else None,
            }
        )
        if len(out) >= limit:
            break
    return out
