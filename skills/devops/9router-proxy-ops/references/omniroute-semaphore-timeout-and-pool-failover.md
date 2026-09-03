# OmniRoute Semaphore Timeout & Pool Cascading Failover

## Overview & Symptoms
When operating multi-account Antigravity pools (e.g. `ag-gemini-pool-3` on `:20129`), you may observe:
1. **Severe latency spikes (30s per attempt)**: Requests hang for exactly 30,000ms before failing or failing over.
2. **Error logs**: `Semaphore timeout after 30000ms for antigravity:<connection_id>`.
3. **Cascading spillover draining starter accounts first**: Starter/Free tier accounts at the tail of the combo (e.g. `pool-13 (starter-quota)`) get drained quickly with 429 quota exhaustion because upstream accounts are stalled or in 403 error states.
4. **Traffic collapse onto single survivor**: One active account receives hundreds of consecutive requests while other accounts appear bypassed.

## Root Cause Analysis
- **Codebase Path**: `C:\Users\Kibe\OmniRoute\open-sse\services\accountSemaphore.ts` (and `chatCore.ts`).
- **Mechanism**:
  - Each account/connection has an in-memory gate limiting concurrent requests (`maxConcurrency: 5` or `2`).
  - When an account hits upstream errors (such as `403 Validation Required` or `429 Rate Limit`), `markBlocked()` puts the gate into a temporary cooldown (`blockedUntil = Date.now() + cooldownMs`).
  - **The Flaw**: `acquire()` checks `if (gate.running < gate.maxConcurrency && !isBlocked(gate))`. When blocked or full, instead of rejecting immediately (fail-fast), it enqueues the request into `gate.queue` and sets a **30-second timer** (`timeoutMs: 30000`).
  - While waiting in the queue, clients often abort (`499 Request aborted`), and when the timer expires it rejects with `SEMAPHORE_TIMEOUT`.
  - Only after 30 seconds does the combo strategy receive the error and attempt the next target in the priority list.

## Pitfall: Why Increasing Semaphore Timeout Worsens the Problem
- Increasing `DEFAULT_TIMEOUT_MS` (e.g., from 30s to 90s) in `accountSemaphore.ts` is counterproductive in a multi-account pool.
- Instead of quickly bypassing an unhealthy account, each request gets trapped in the queue for **90 seconds** before failing over. This leads to massive client-side timeouts (`499 Request aborted`), broken chat streams, and complete pool paralysis.

## Cascading Failover Lifecycle
1. **Upstream Quota/Validation Fault**: Upper accounts (`pool-1` .. `pool-10`) exhaust daily quota or hit 403 validation.
2. **Semaphore Queue Stall**: Account at `pool-11` gets blocked and stalls requests for 30s each.
3. **Deep Spillover**: Requests spill over to `pool-12` (Pro) and `pool-13` (Starter Standby).
4. **Starter Exhaustion**: Because Starter accounts have low quota limits (~50 requests), they hit 429 almost immediately while Pro accounts continue taking hundreds of requests.
5. **Full Pool Lockout**: Once the remaining Pro account hits quota limit, all 13 accounts are exhausted/blocked, resulting in the gateway reporting: `The model provider is rate-limiting requests. Please wait a moment and try again.`

## Timezone Note for Diagnostics
- **OmniRoute SQLite (`storage.sqlite`)** stores timestamps strictly in **UTC ISO 8601** (`...Z`).
- **Vietnam Time (ICT / GMT+7)** = `UTC + 7 hours`.
  - Example: `13:51 UTC` $\rightarrow$ `20:51 (8:51 PM ICT)`.
  - Example: `15:46 UTC` $\rightarrow$ `22:46 (10:46 PM ICT)`.
- Always convert UTC timestamps to local ICT before comparing with user chat timestamps.

## Remediation & Fix Direction
In `open-sse/services/accountSemaphore.ts`:
- When `isBlocked(gate)` is `true`, `acquire()` should **fail-fast immediately** with `SEMAPHORE_BLOCKED` rather than enqueueing with a 30s timeout.
- This allows combo routers to advance to the next candidate in **0ms** without stalling the user session or triggering client 499 aborts.

## OmniRoute In-App Auto-Update & Custom Patch Preservation
- **In-App Auto-Update Behavior**: Updating via the OmniRoute UI triggers `autoUpdate.ts` (`git stash` $\rightarrow$ `git fetch` $\rightarrow$ `git checkout <targetTag>` $\rightarrow$ `npm run build`), which resets local source modifications back to the upstream release tag.
- **Config & DB Safety**: Account credentials, OAuth tokens, combos, and proxy assignments reside in `C:\Users\Kibe\.omniroute\storage.sqlite` and are **never lost** during updates.
- **Preserving Custom Fixes**:
  1. Save local changes as a patch file: `git diff > failfast_semaphore.patch`.
  2. After clicking Update in the App, re-apply the patch:
     ```bash
     git apply failfast_semaphore.patch && npm run build
     ```
