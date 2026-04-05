from datetime import date

from pydantic import BaseModel, Field, HttpUrl


class FilingRecord(BaseModel):
    cik: str
    accession: str
    form: str
    filed: date
    primary_document: str | None = None
    filing_url: HttpUrl | None = None
    description: str | None = None
