"""Filing index helpers for EDGAR archive paths."""

from __future__ import annotations


def accession_to_path_parts(cik_numeric: str, accession: str) -> tuple[str, str]:
    acc_nodash = accession.replace("-", "")
    cik_int = str(int(cik_numeric))
    return cik_int, acc_nodash
