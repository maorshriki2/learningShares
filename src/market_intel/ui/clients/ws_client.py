from __future__ import annotations

import json
import queue
import threading
from typing import Any, Callable
from urllib.parse import urlparse

import websocket


def http_to_ws_base(api_base: str) -> str:
    p = urlparse(api_base)
    scheme = "wss" if p.scheme == "https" else "ws"
    return f"{scheme}://{p.netloc}"


class MarketIntelWebSocketClient:
    def __init__(self, api_base: str, symbol: str, on_message: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._url = f"{http_to_ws_base(api_base)}/api/v1/ws/market/{symbol.upper()}"
        self._q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=200)
        self._on_message = on_message
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def _handle(self, _ws: websocket.WebSocketApp, message: str) -> None:
        data = json.loads(message)
        if self._on_message:
            self._on_message(data)
        try:
            self._q.put_nowait(data)
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self._q.put_nowait(data)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def run() -> None:
            self._ws = websocket.WebSocketApp(
                self._url,
                on_message=self._handle,
            )
            while not self._stop.is_set():
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
                if self._stop.is_set():
                    break

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._ws:
            self._ws.close()
        if self._thread:
            self._thread.join(timeout=2.0)

    def drain(self) -> dict[str, Any] | None:
        last: dict[str, Any] | None = None
        while True:
            try:
                last = self._q.get_nowait()
            except queue.Empty:
                break
        return last
