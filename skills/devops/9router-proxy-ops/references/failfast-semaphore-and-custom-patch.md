# OmniRoute/Antigravity Semaphore Incident Reference

## Why this reference exists

Use this when a multi-account Antigravity combo reports requests concentrated on one account, repeated `Semaphore timeout after ...`, `499 Request aborted`, or `409 Hard connection binding mismatch` after a source change.

## Evidence rules learned

1. **Read live evidence before explaining the incident.** Query the live OmniRoute APIs and the actual SQLite `call_logs`; do not infer from a screenshot or from a previous narrative.
2. **Normalize timestamps explicitly.** `call_logs.timestamp` is stored as ISO UTC (`Z`). Report both the raw UTC timestamp and the converted local time, and do not claim a local-time event from a UTC-only value.
3. **Separate account failure from router failure.** A real upstream `403/429` is distinct from a local semaphore timeout, client abort (`499`), quota lockout, and executor binding mismatch (`409`). Group by final persisted `connection_id`/account, not `combo_step_id` alone.
4. **`priority` is ordered spillover, not balancing.** `maxConcurrent` is a cap, not a round-robin selector. Healthy traffic can legitimately skew toward earlier targets; the bug signal is a blocked/failed target being queued for a long timeout instead of being skipped.
5. **Do not add unrelated routing changes while fixing semaphore behavior.** A hard-binding/session-affinity change can create `409 Hard connection binding mismatch` and obscure the original issue. Keep the patch allowlist minimal.

## Known source-level semaphore fix pattern

The account semaphore must reject immediately when an account gate is already blocked/cooling down, rather than enqueueing a waiter:

- `open-sse/services/accountSemaphore.ts`: `isBlocked(gate)` -> immediate `SEMAPHORE_BLOCKED` rejection.
- `open-sse/services/rateLimitSemaphore.ts`: `isRateLimited(gate)` -> immediate `SEMAPHORE_RATE_LIMITED` rejection.
- `open-sse/services/combo.ts`: treat both codes as immediate failover to the next target.
- `open-sse/handlers/chatCore/streamErrorResult.ts`: classify both codes as semaphore-capacity errors where the handler needs that classification.

Do not increase the queue timeout as a substitute; that makes blocked traffic wait longer. Do not reset OAuth, delete accounts, alter proxy assignments, or mutate raw SQLite to solve this symptom.

## Safe source-change workflow

1. Inspect `git status` and the exact diff before editing; preserve unrelated dirty changes.
2. Patch only the four semaphore files above unless a separate, verified issue requires more.
3. Run `npm run typecheck:core` before restarting. A stray brace or removed interface field can break the source even if an old production build still serves traffic.
4. Run `npm run build` and require a real successful exit. A timeout during page generation or standalone assembly is **not** a passed build.
5. Restart OmniRoute only after the build passes; expect in-flight requests to drop during restart, but do not touch the database/config.
6. Verify port `20129`, `/api/combos`, `/api/providers`, `/api/rate-limits`, and one bounded canary request. Report the actual HTTP status and any remaining warnings.

## Custom patch persistence

Keep the patch outside the OmniRoute checkout, for example under `D:\Taadaa\AI-Tools\patches\`. After an app update, regenerate or apply a patch against the exact new source revision and rerun typecheck/build. Never assume a patch applies merely because the file names match: use `git apply --check`, and if it fails, inspect the current diff and rebase the patch manually. A patch generated from the current working tree will not apply to that same already-patched tree.

## Reporting format

- **Mục đích**
- **Kết quả live**: API/DB evidence, raw UTC + local conversion
- **Root cause confirmed** vs **hypothesis**
- **Change scope**: exact files changed
- **Verification**: typecheck, build, restart, canary
- **Blocker**: only if a command actually failed; do not invent a successful result
