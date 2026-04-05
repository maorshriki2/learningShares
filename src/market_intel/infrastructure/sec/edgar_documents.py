from __future__ import annotations


def filing_document_url(cik_numeric: str, accession: str, primary_document: str) -> str:
    acc_nodash = accession.replace("-", "")
    cik_int = str(int(cik_numeric))
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{primary_document}"
    )
