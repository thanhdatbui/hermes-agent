# OmniRoute Semaphore Hotfix Verification

## Trigger
Use when an Antigravity/Gemini account shows quota but exact-account requests fail with HTTP 429.

## Evidence-first classification
1. Canary the exact connection with `x-omniroute-connection`; do not infer from a pool-level request.
2. Capture the raw body and elapsed time.
3. Classify before changing quota or account state:
   - `Semaphore timeout after 30000ms` (or similar) = Omni internal queue/semaphore timeout, not Google quota.
   - Google `RESOURCE_EXHAUSTED`, explicit quota/reset text = upstream quota/rate limit.
   - 401/403 or explicit tier/model denial = auth/entitlement; do not call it quota exhaustion.
4. A 429 taking ~30s with `SEMAPHORE_TIMEOUT` is a router concurrency problem. Preserve the account; do not deactivate it.

## Patch decomposition rule
Do not dispatch a broad routing investigation and implementation as one worker task. Use bounded lanes:
1. Lane A: exact source anchor and data-flow inspection.
2. Lane B: one narrow code change to pass combo queue timeout into semaphore acquisition.
3. Lane C: focused unit test.
4. Lane D: production build/restart and fresh canary.
Each lane has an explicit file allowlist, max calls, and an abort rule. A worker returning `0 files modified` is failure; do not retry the same broad contract. Reduce to a single exact anchor or ask for a new contract.

## Source → bundle → runtime gate
A source edit is not a fix in production. Verify all three:
- source diff contains the intended `timeoutMs` at the unique `acquireAccountSemaphore` call;
- production backend bundle mtime is newer than the source edit and was built with the backend-only build command;
- the listening OmniRoute process restarted after the bundle build.
Only then run a fresh exact-connection canary and inspect the raw body. If the raw body still says `Semaphore timeout after 30000ms`, report runtime stale or patch absent; never claim success.

## Known pitfall
Changing `DEFAULT_TIMEOUT_MS` alone is not equivalent to passing combo `queueTimeoutMs`. It may affect non-combo requests and can even lengthen the observed timeout. The combo path must explicitly pass a bounded timeout (normally ~1000ms) so a saturated account spills to another target.
