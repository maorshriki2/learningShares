from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from market_intel.domain.value_objects.timeframe import Timeframe
from market_intel.infrastructure.market_data.provider_chain import stream_trade_ticks
from market_intel.modules.charting.candle_builder import CandleBuilder

router = APIRouter(tags=["market-ws"])


@router.websocket("/ws/market/{symbol}")
async def market_ws(websocket: WebSocket, symbol: str) -> None:
    await websocket.accept()
    state = websocket.app.state.app_state
    builder = CandleBuilder(symbol=symbol.upper(), timeframe=Timeframe.M1)
    stream = stream_trade_ticks(state.settings, symbol.upper())
    try:
        async for tick in stream:
            builder.push(tick)
            candles = builder.to_candles()
            payload = {
                "type": "tick",
                "tick": {
                    "symbol": tick.symbol,
                    "ts": tick.ts.isoformat(),
                    "price": tick.price,
                    "size": tick.size,
                    "source": tick.source,
                },
                "candles": [
                    {
                        "ts": c.ts.isoformat(),
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume,
                    }
                    for c in candles[-120:]
                ],
            }
            await websocket.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(0.12)
    except WebSocketDisconnect:
        return
