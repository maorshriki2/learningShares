## Fundamentals Agent — Architecture skeleton

### Goal
Serve as the **fundamental analysis specialist**: business quality, financial statements, valuation, and model governance.

### Inputs (planned)
- **Analysis artifact** (UI-side cache key: `analysis_artifact:v1`)
- Fundamentals payloads (ROIC/WACC, Piotroski, DCF sensitivity, statements)

### Outputs (planned)
- Structured “verdict” objects that can be embedded into the unified artifact
- Human-facing explanations (Hebrew + finance terms), with traceability to inputs

### Boundaries (current)
- This folder is **infrastructure only** right now.
- No data fetching, no model execution, no side effects.

