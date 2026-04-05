from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import websockets

from market_intel.domain.entities.tick import TradeTick


async def stream_finnhub_trades(api_key: str, symbol: str) -> AsyncIterator[TradeTick]:
    sym = symbol.upper()
    uri = f"wss://ws.finnhub.io?token={api_key}"
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps({"type": "subscribe", "symbol": sym}))
        while True:
            raw = await ws.recv()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            msg = json.loads(raw)
            if msg.get("type") != "trade":
                continue
            data = msg.get("data") or []
            for row in data:
                if row.get("s") != sym:
                    continue
                price = row.get("p")
                ts_ms = row.get("t")
                vol = row.get("v", 0)
                if price is None or ts_ms is None:
                    continue
                ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                yield TradeTick(
                    symbol=sym,
                    ts=ts,
                    price=float(price),
                    size=float(vol or 0),
                    exchange=None,
                    conditions=None,
                    source="finnhub",
                )
            await asyncio.sleep(0)
