## Final Verdict Learning Agent — Architecture skeleton

### Goal
Compose a **single coherent final verdict** across fundamentals, technicals, and market context,
and turn it into a learning loop (what to check next, what would change the verdict).

### Inputs (planned)
- Unified analysis artifact `analysis_artifact:v1`
- Composed payload: `stock360` (already aggregated server-side)

### Outputs (planned)
- A final verdict object with:
  - thesis
  - risk register
  - key drivers & disconfirming signals
  - learning checklist

### Boundaries (current)
- This folder is **infrastructure only** right now.
- No new computations; just reserved structure for future orchestration.

