# Farm Alert timeout and policy closeout

## Worker lane budgets

- Read-only evidence/triage: 120s.
- Exact patch or policy-doc edit: 180–240s.
- Scoped code surgery: 300s.
- Runtime/canary: 600s with event-driven completion.
- Long batch/build: background launcher plus out-of-band monitor, never a code worker.

Split mixed work before dispatch. Each worker gets one lane, exact file/region allowlist, one acceptance command, and a fail-fast checkpoint within the first three iterations. On timeout, inspect the shared workspace and diff before redispatch; a valid partial edit is parent-verifiable evidence. If no artifact exists, retry only with a materially narrower contract, never the same prompt.

Timeouts are transient and do not consume the structural failure budget, but allow at most two transport retries with backoff. Then change lane/contract or escalate. Never run concurrent workers on the same file/region. Use `notify_on_complete`, not polling loops.

For policy-only closeout, use a deterministic offline validator for changed policy files before the reviewer. A repository-wide pytest timeout indicates unsuitable test mapping, not policy failure; use the gate's supported skip-test mode only while retaining the independent reviewer gate.

Reviewer endpoint distinction: `invoke_sol_audit.py` uses the 9Router coding endpoint; `sol_auditor.py` uses the ChatGPT-Web judge endpoint. A 404 is a route/model mismatch, not a verdict; probe the endpoint/catalog or use an authorized fallback.

User corrections such as “A–Z, do not stop and ask” or “session-close means commit/push” must be embedded in the class-level skill and policy, not only session memory.
