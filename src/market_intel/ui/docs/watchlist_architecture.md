# Watchlist Architecture (Snapshot + Near‑Real‑Time)

## Goal
Provide a **fast watchlist** that:
- Loads meaningful content in \<2s (top tickers per sector and market‑cap bucket).
- Refreshes **price** frequently (seconds) without re‑computing heavy analytics.
- Degrades gracefully when a data provider is unavailable.

This document describes the intended data layers, TTL policy, and fallbacks.

## Data Layers

### 1) Snapshot Layer (cached)
**Purpose**: stable list composition and sorting (Top‑N per sector/bucket).

- **Endpoint**: `GET /api/v1/watchlist/sector-buckets`
- **Payload**: sectors → {Large Cap/Mid Cap/Small Cap} → [{symbol, name, market_cap, price, beta, ...}]
- **Refresh cadence**: every 5–15 minutes (server), with UI cache TTL smaller if desired.

### 2) Live Price Layer (near‑real‑time)
**Purpose**: update only fields that change rapidly.

- **Fields**: `price`, `change_pct`, `volume` (when available).
- **Cadence**: every 5–30 seconds (depending on provider and quotas).
- **Important**: does **not** recompute `volatility_1y`, `beta`, DCF, fundamentals.

## TTL Policy (recommended)
- **Price**: 5–30 seconds
- **Market cap / sector / name**: hours–1 day
- **Beta**: days
- **Volatility (1Y)**: daily/weekly

Rationale: avoid expensive history calls and keep UX responsive.

## Fallback Strategy

### When `FMP_API_KEY` is missing or provider fails
`/api/v1/watchlist/sector-buckets` may return `{ok:false, message:...}`.

Fallback options:
1) **Static universe fallback** (slower): iterate a known ticker universe and call
   `GET /api/v1/instruments/{symbol}/summary` per symbol.
2) Show **last known snapshot** (server cache) and a banner: “data may be stale”.

The system should prefer (2) if server persistence exists (Redis/DB), otherwise (1).

## Scaling Notes
- Snapshot endpoint is optimized to **1 request per sector per refresh** (server-side).
- Live price should be **batched** (WS/polling for multiple symbols) when possible.
- Avoid per‑symbol historical calls inside watchlist refresh loops.

## User Experience
- Default view: snapshot list + “last updated” timestamp.
- Explicit refresh button: forces snapshot reload.
- Optional toggle: “Live prices” (may increase network usage).

