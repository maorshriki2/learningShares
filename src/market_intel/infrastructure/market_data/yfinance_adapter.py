"""Compatibility shim — historical access lives in historical_bars."""

from market_intel.infrastructure.market_data.historical_bars import YFinanceHistoricalAdapter

__all__ = ["YFinanceHistoricalAdapter"]
