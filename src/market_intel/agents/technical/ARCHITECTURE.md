## Technical Agent — Architecture skeleton

### Goal
Serve as the **price-action / chart specialist**: OHLCV, indicators, pattern engines, and timeframe-aware reasoning.

### Inputs (planned)
- Artifact inputs: `ohlcv` (candles, indicators, patterns, fibonacci)
- Artifact verdicts: `chart_technical_verdict`

### Outputs (planned)
- Structured technical verdicts (trend, momentum, volatility regimes, key levels)
- Explanations that link directly to computed features (not opinions)

### Boundaries (current)
- This folder is **infrastructure only** right now.
- No recomputation in UI; consumes existing cached artifact payloads.

