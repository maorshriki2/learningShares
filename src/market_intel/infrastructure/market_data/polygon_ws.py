from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import websockets

from market_intel.domain.entities.tick import TradeTick


async def stream_polygon_trades(api_key: str, symbol: str) -> AsyncIterator[TradeTick]:
    sym = symbol.upper()
    uri = f"wss://socket.polygon.io/stocks"
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps({"action": "auth", "params": api_key}))
        await ws.send(json.dumps({"action": "subscribe", "params": f"T.{sym}"}))
        while True:
            raw = await ws.recv()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            for msg in json.loads(raw):
                ev = msg.get("ev")
                if ev != "T":
                    continue
                sym_m = msg.get("sym")
                if sym_m and sym_m.upper() != sym:
                    continue
                price = msg.get("p")
                size = msg.get("s", 0)
                ts_ns = msg.get("t")
                if price is None or ts_ns is None:
                    continue
                ts = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)
                yield TradeTick(
                    symbol=sym,
                    ts=ts,
                    price=float(price),
                    size=float(size or 0),
                    exchange=msg.get("x"),
                    conditions=None,
                    source="polygon",
                )
            await asyncio.sleep(0)
