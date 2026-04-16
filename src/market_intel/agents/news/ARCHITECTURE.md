## News Agent — Architecture skeleton

### Goal
Serve as the **market context / news specialist**: events, narratives, catalysts, and source-checking.

### Inputs (planned)
- Context feed payloads (artifact input: `market_context_feed`)
- Optional live refresh snapshots cached under `market_context_feed:v1`

### Outputs (planned)
- Ranked/contextualized items with confidence & source metadata
- Learning prompts (what to verify, what to ignore, how to reason)

### Boundaries (current)
- This folder is **infrastructure only** right now.
- No scraping, no external calls, no model execution.

