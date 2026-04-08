from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from market_intel.api.lifespan import app_lifespan
from market_intel.api.middleware.exception_handlers import register_exception_handlers
from market_intel.api.routers import (
    analysis,
    blind_test,
    fundamentals,
    governance,
    health,
    instruments,
    macro,
    market_rest,
    market_ws,
    peers,
    portfolio,
    portfolio_alpha,
    sentiment,
    stock360,
    valuation,
    watchlist,
)

app = FastAPI(title="Market Intel API", version="0.1.0", lifespan=app_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

app.include_router(health.router, prefix="/api/v1")
app.include_router(market_rest.router, prefix="/api/v1")
app.include_router(market_ws.router, prefix="/api/v1")
app.include_router(instruments.router, prefix="/api/v1")
app.include_router(fundamentals.router, prefix="/api/v1")
app.include_router(governance.router, prefix="/api/v1")
app.include_router(sentiment.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(peers.router, prefix="/api/v1")
app.include_router(macro.router, prefix="/api/v1")
app.include_router(blind_test.router, prefix="/api/v1")
app.include_router(portfolio_alpha.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(stock360.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(valuation.router, prefix="/api/v1")
