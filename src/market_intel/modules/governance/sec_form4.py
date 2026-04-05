"""Form 4 parsing helpers used by SEC infrastructure adapters."""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from xml.etree import ElementTree as ET

from market_intel.domain.entities.insider_transaction import InsiderTransaction


def parse_form4_xml_to_transactions(
    symbol: str,
    xml_text: str,
    default_filing_date: date | None = None,
) -> list[InsiderTransaction]:
    """
    Lightweight Form 4 XML parse using regex fallbacks when namespaces vary.
    Not a full SEC schema validator; sufficient for educational dashboards.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return _regex_fallback_form4(symbol, xml_text, default_filing_date)

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0].strip("{")
    nsmap = {"edgar": ns} if ns else {}

    def findall_local(name: str) -> list[Any]:
        if nsmap:
            return root.findall(f".//{{{ns}}}{name}")
        return root.findall(f".//{name}")

    reporting_name = None
    for tag in ("reportingOwner", "reportingOwnerId", "rptOwnerName"):
        el = findall_local("reportingOwner")
        if el:
            for child in el[0].iter():
                if child.tag.endswith("name") or child.tag.endswith("rptOwnerName"):
                    if child.text:
                        reporting_name = child.text.strip()
                        break
        if reporting_name:
            break

    transactions: list[InsiderTransaction] = []
    non_deriv = findall_local("nonDerivativeTransaction")
    for tx in non_deriv:
        tx_date = None
        code = None
        shares = None
        price = None
        for child in tx.iter():
            local = child.tag.split("}")[-1]
            if local == "transactionDate" and child.text:
                tx_date = _parse_date(child.text.strip())
            elif local == "transactionCode" and child.text:
                code = child.text.strip()
            elif local in ("transactionShares", "transactionSharesOwnedFollowingTransaction"):
                if child.text:
                    try:
                        shares = float(child.text)
                    except ValueError:
                        shares = None
            elif local == "transactionPricePerShare" and child.text:
                try:
                    price = float(child.text)
                except ValueError:
                    price = None
        if tx_date is None or shares is None:
            continue
        ttype = code or "nonDerivativeTransaction"
        insider = reporting_name or "Unknown Insider"
        value = shares * price if price is not None else None
        transactions.append(
            InsiderTransaction(
                symbol=symbol,
                insider_name=insider,
                insider_title=None,
                transaction_type=ttype,
                shares=abs(shares),
                price_per_share=price,
                value_usd=value,
                transaction_date=tx_date,
                filing_date=default_filing_date or tx_date,
                ownership_nature=None,
            )
        )
    if transactions:
        return transactions
    return _regex_fallback_form4(symbol, xml_text, default_filing_date)


def _parse_date(s: str) -> date | None:
    try:
        y, m, d = s[:10].split("-")
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def _regex_fallback_form4(
    symbol: str,
    xml_text: str,
    default_filing_date: date | None,
) -> list[InsiderTransaction]:
    out: list[InsiderTransaction] = []
    dates = re.findall(
        r"<transactionDate>\s*<value>(\d{4}-\d{2}-\d{2})</value>",
        xml_text,
    )
    shares = re.findall(
        r"<transactionShares>\s*<value>([0-9.]+)</value>",
        xml_text,
    )
    codes = re.findall(
        r"<transactionCode>\s*<value>([A-Z])</value>",
        xml_text,
    )
    n = min(len(dates), len(shares))
    for i in range(n):
        td = _parse_date(dates[i])
        if td is None:
            continue
        try:
            sh = float(shares[i])
        except ValueError:
            continue
        code = codes[i] if i < len(codes) else "U"
        fd = default_filing_date or td
        out.append(
            InsiderTransaction(
                symbol=symbol,
                insider_name="Insider (parsed)",
                insider_title=None,
                transaction_type=code,
                shares=abs(sh),
                price_per_share=None,
                value_usd=None,
                transaction_date=td,
                filing_date=fd,
                ownership_nature=None,
            )
        )
    return out
