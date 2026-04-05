from __future__ import annotations

_PEER_MAP: dict[str, list[str]] = {
    "AAPL":  ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
    "MSFT":  ["AAPL", "GOOGL", "META", "AMZN", "NVDA"],
    "GOOGL": ["MSFT", "META", "AAPL", "AMZN", "SNAP"],
    "META":  ["GOOGL", "SNAP", "PINS", "TWTR", "YELP"],
    "AMZN":  ["MSFT", "GOOGL", "AAPL", "EBAY", "WMT"],
    "NVDA":  ["AMD", "INTC", "AVGO", "QCOM", "MU"],
    "AMD":   ["NVDA", "INTC", "AVGO", "QCOM", "MU"],
    "INTC":  ["AMD", "NVDA", "AVGO", "QCOM", "TXN"],
    "TSLA":  ["GM", "F", "RIVN", "LCID", "NIO"],
    "GM":    ["TSLA", "F", "STLA", "TM", "HMC"],
    "F":     ["GM", "TSLA", "STLA", "TM", "HMC"],
    "JPM":   ["BAC", "WFC", "C", "GS", "MS"],
    "BAC":   ["JPM", "WFC", "C", "GS", "USB"],
    "WFC":   ["JPM", "BAC", "C", "USB", "TFC"],
    "GS":    ["MS", "JPM", "BAC", "C", "BLK"],
    "XOM":   ["CVX", "COP", "BP", "SHEL", "TTE"],
    "CVX":   ["XOM", "COP", "BP", "SHEL", "TTE"],
    "JNJ":   ["PFE", "MRK", "ABT", "UNH", "ABBV"],
    "PFE":   ["JNJ", "MRK", "LLY", "ABBV", "BMY"],
    "UNH":   ["CVS", "CI", "HUM", "CNC", "MOH"],
    "WMT":   ["TGT", "COST", "AMZN", "KR", "DG"],
    "TGT":   ["WMT", "COST", "KR", "DG", "DLTR"],
    "COST":  ["WMT", "TGT", "BJ", "SFM", "KR"],
    "DIS":   ["NFLX", "CMCSA", "PARA", "WBD", "AMZN"],
    "NFLX":  ["DIS", "CMCSA", "PARA", "WBD", "SPOT"],
    "SPY":   ["QQQ", "IWM", "VOO", "DIA", "VTI"],
}

_INDUSTRY_FALLBACKS: dict[str, list[str]] = {
    "Technology":            ["MSFT", "AAPL", "GOOGL", "NVDA", "META"],
    "Financial Services":    ["JPM", "BAC", "GS", "MS", "WFC"],
    "Financials":            ["JPM", "BAC", "GS", "MS", "WFC"],
    "Healthcare":            ["JNJ", "PFE", "UNH", "MRK", "ABT"],
    "Consumer Cyclical":     ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Consumer Defensive":    ["WMT", "PG", "KO", "PEP", "COST"],
    "Energy":                ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Communication Services":["GOOGL", "META", "DIS", "NFLX", "T"],
    "Industrials":           ["HON", "CAT", "GE", "UPS", "RTX"],
    "Utilities":             ["NEE", "DUK", "SO", "D", "AEP"],
    "Basic Materials":       ["LIN", "APD", "ECL", "FCX", "NEM"],
    "Real Estate":           ["AMT", "PLD", "EQIX", "CCI", "SPG"],
}


def lookup_peers(symbol: str, industry: str | None = None) -> list[str]:
    sym = symbol.upper()
    if sym in _PEER_MAP:
        return _PEER_MAP[sym]
    if industry and industry in _INDUSTRY_FALLBACKS:
        peers = [p for p in _INDUSTRY_FALLBACKS[industry] if p != sym]
        return peers[:5]
    return []
