from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


def retry_async() -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    return retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(
            (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            )
        ),
    )
