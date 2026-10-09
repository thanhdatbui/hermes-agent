# Budget, timestamp, and released-follow audit

Use this checklist whenever a user asks whether today's cross-follows were released or whether the bot respected budget.

## 1. Separate the numbers
Report three different quantities:
- **Configured budget:** design target read from the live runner/config; never infer it from today's output.
- **Attempted:** aggregate/session telemetry; may include actions TikTok rejected.
- **Committed:** verified `follow_result.json` `followed` entries / server-confirmed actions.

A result of 3–8 follows per session is an observed outcome, not proof that the configured budget is 3–8. Early `FOLLOW_FAILED`, cooldown, organic-rest cohort, account age/video gates, and fail-closed shutdown can all reduce output.

Current design reference: approximately 15–20 follows/session (recommended 15–18), around 40/day; observed successful output may be much lower (~8–14/account/shift) after gates. If the live config was not inspected, say so explicitly.

## 2. Align timestamps
For dashboard deltas, use the same account-level snapshot pair for Follower and Following and print both timestamps. A daily full-scrape delta is not comparable to today's partial bot-progress counter. For per-session reconciliation use T0 (pre-session) → T1 (post-session).

## 3. Audit released accounts
For every account that committed cross-follows today:
1. Read the session `follow_result.json`: `status`, `followed`, `follow_failed`.
2. Compare the committed list with Web Following snapshots before/after the session.
3. Check available historical snapshots for drops, but do not claim “never released” unless the full available history was actually inspected.
4. For `FOLLOW_FAILED` with zero committed follows, report attempted and committed separately and keep the session fail-closed.

Evidence precedence: per-machine verified result > aggregate action ledger > Web snapshot delta. Never treat an attempt ledger as proof of a committed follow or reclassify rejected cross-follows as natural follows.
