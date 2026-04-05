from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from market_intel.api.dependencies import AppState, build_app_state
from market_intel.config.settings import get_settings


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    state: AppState = await build_app_state(settings)
    app.state.app_state = state
    yield
    await state.http_client.aclose()
