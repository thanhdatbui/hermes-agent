# 9Router Quota Priority & Cooldown Pitfalls

## 1. The One-Way 9999 Demotion Trap
- **Issue:** If server-side error handling (`2283.js`) writes `priority = 9999` directly to SQLite on a 429/quota error, but recovery only runs in a client-side Quota Tracker page, accounts become permanently trapped at `9999` when the browser tab is closed.
- **Rule:** Recovery must run on the server-side selection/read path. A background timer is optional; client-only polling is not sufficient.

## 2. Required State Separation
`9999` is an effective temporary scheduling priority, not the account's permanent/base priority. Preserve:

- `priorityBase`: stable order for the account.
- `priority`: effective order (`9999` while cooling down, otherwise `priorityBase`).
- `priorityCooldownUntil`: expiry timestamp.
- `isActive`: unchanged unless explicitly requested.

Prefer the upstream reset timestamp; use a bounded fallback only when no reset time is available. Do not overwrite `priorityBase` when demoting.

## 3. Schema Before Data Repair
Inspect `PRAGMA table_info(providerConnections)` and the serialized connection JSON before writing. Do not assume `priorityBase` or `priorityCooldownUntil` are SQLite columns. If absent, either use an application-supported JSON field or add a proper migration; never issue an invalid SQL update against a missing column. Preserve credentials and provider-specific data.

## 4. Selection and Recovery Algorithm
1. Load active provider connections.
2. If a cooldown is expired, restore effective priority from `priorityBase` and clear the expiry.
3. Exclude only connections whose cooldown is still in the future.
4. Sort by effective priority, retaining existing last-used/round-robin tie-breakers.
5. On 429/quota, save the old base priority, then write `9999` plus the expiry.
6. Keep this logic server-side so it works without an open UI.

## 5. Reorder-Path Trap
Audit every generic reorder/normalize routine and every PUT/update route. A helper that re-indexes every row to `1..N` after each update can erase the base priority or immediately undo recovery. Reorder must preserve the saved base priority and use `9999` only while the cooldown is active. Verify with a two-account fixture or dry-run ordering check.

## 6. Installed Next.js Bundle Workflow (Windows)
1. Identify the active package, process, and DB.
2. Make timestamped backups before editing a minified bundle or DB.
3. Patch the smallest exact substring; avoid broad replacements in one-line bundles.
4. Run `node --check` with normalized Windows paths.
5. Restart through the existing supervisor/watchdog when possible. A PID returned by `Start-Process` may not own `:20128`; verify the actual listener PID with `netstat -ano` and process inspection.
6. Smoke-test `/api/health` and inspect sanitized connection ordering/active flags.
7. For the quota 9999 trap, validate the effective selection path, not only DB recovery: an Antigravity connection with `priority >= 9000` and a future `priorityCooldownUntil` must be excluded from request selection. Otherwise each retry can hit another cooling account and recreate all-accounts-9999.
8. Audit every reorder/normalize and PUT/update path. Generic re-indexing must not overwrite Antigravity `priorityBase`; expired cooldowns restore `priority` from that saved base, while active cooldowns retain effective priority `9999`.
9. Final DB invariants: every active Antigravity row has a unique `priorityBase`; each `priority >= 9000` has an active future cooldown; no credentials are printed.

## 7. Verification Checklist
- No token or credential values in logs or reports.
- Syntax checks pass for every edited bundle.
- `/api/health` succeeds.
- Active Antigravity connections have distinct base priorities.
- Expired cooldown restores base priority; active cooldown remains demoted.
- Reorder/PUT does not destroy base metadata.
- No account is silently disabled; proxy/model settings remain unchanged.

## 8. Provider Quota Separation
Antigravity can expose separate quota pools for Gemini versus Claude/GPT-OSS. Define the priority policy against the model pool actually used by the workflow; do not treat one model's exhaustion as proof that every model pool or every account is exhausted.
