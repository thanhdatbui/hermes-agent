# Farm Alert Auto A–Z (user-corrected 2026-09-26)

When a user sends a Farm Alert with a concrete machine/error, treat it as a closed-loop execution trigger—not a diagnosis-only request and not a permission request.

## State machine
`ALERT → EVIDENCE → CLASSIFY → WORKER → VERIFY → CANARY → DONE/BLOCKED`

- **EVIDENCE:** inspect the current run's exact log window, matching XML and screenshot, serial/host/workbook mapping, and lock state. Never use an unrelated old batch artifact.
- **CLASSIFY:** separate `TRANSIENT` (timeout/429/5xx/worker no-response), `STRUCTURAL` (parser/selector/state/code), `INFRA` (offline/serial/ADB), and `BUSINESS/OWNERSHIP`.
- **WORKER:** dispatch an exact patch contract for structural defects. Worker changes/test offline only; no live ADB. Coordinator independently verifies status, diff/numstat, scope, and test result; worker self-report is not evidence.
- **Recovery ladder:** R1 bounded transient retry; R2 structural redispatch with a materially different hypothesis/scope/acceptance; R3 emergency surgery only when the exact diff is known, max one surgery per alert, max two files and 30 changed lines, and never credentials/workbook/device state/lock/logout/config; R4 pivot to the correct host/mapping/runner and return to EVIDENCE. Never blind-retry or resend the same contract.
- **CANARY:** after verification, run the canonical runner on the correct cluster and one target first; inspect final status and fresh artifacts before widening.
- **Before BLOCKED:** execute every applicable recovery branch and record evidence/ledger. Do not stop merely because diagnosis is complete, a worker finished, or a routine canary is pending.
- **Ask only at four gates:** missing credentials; business/ownership decision; irreversible or paid action; or all practical escalation branches are exhausted. Never ask “should I continue/canary/dispatch?” for an in-budget step.

Preserve FARM-ASSET-001, no manual ADB taps, no broad scans, lock retention, visual evidence, and closeout gates. Canonical detailed workflow: `docs/ai/workflows/farm-alert-coordinator-loop.md`.
