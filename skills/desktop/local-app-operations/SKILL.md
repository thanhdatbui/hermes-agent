---
name: local-app-operations
description: "Safely update and operate locally hosted web applications through their installed/runtime surface, keeping application management separate from source-repository maintenance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [local-app, web-dashboard, app-update, browser-ui, proxy-import, credential-safety]
    category: desktop
---

# Local application operations

Use this skill when the user asks to update, configure, log into, or import data into a locally running application with a browser dashboard (for example, a gateway, proxy manager, or self-hosted admin UI).

## Core rule: app surface first, repository second

1. Interpret “update the app” as updating the installed/running application instance, not automatically updating its source repository.
2. Discover the runtime surface first: URL/port, process owner, installed package/shortcut, in-app version, and available updater or admin controls.
3. Do not enter a source repository, run `git fetch`, `rebase`, `reset --hard`, `stash`, or overwrite local code unless the user explicitly asks to update the source checkout or the application is demonstrably installed from that checkout and no safer app updater exists.
4. Never involve an unrelated repository merely because it is present on the machine. State the exact target path and port before acting.
5. Do not stop a process as a default prerequisite. Update through the app's own updater or package mechanism first. Restart only when required by the update and only after checking the process/port and scope.
6. If a source-based update is truly required, preserve local work visibly (named backup/stash/branch), report the exact conflict risk, and verify the application only after the update/build succeeds. Never silently discard local work.

## Operational sequence

1. **Scope lock:** write down target app, URL/port, allowed side effects, and explicit non-goals. For OmniRoute-like setups, keep its port separate from a neighboring gateway.
2. **Inspect, do not mutate:** check the app page/version, runtime process, endpoint health, and available UI controls. Use browser UI for settings and imports; use terminal only for read-only discovery unless the user explicitly authorized a runtime update.
3. **Credentials:** never echo, save, export, or repeat passwords, API keys, OAuth tokens, or workbook credentials. If the user explicitly supplies a credential for a local login, type it only into the intended field and do not include it in reports or logs. Prefer disabling the dashboard password through the app's Security settings when the user explicitly requests it; otherwise use the browser's session/password manager rather than source edits or plaintext automation.
4. **Configuration:** change settings through the application's own UI/API. After each state-changing click, refresh the accessibility snapshot and verify the resulting state.
5. **Configuration:** change settings through the application's own UI/API. After each state-changing click, refresh the accessibility snapshot and verify the resulting state.
6. **Catalog boundary:** distinguish the application's upstream `/v1/models` catalog from the client/model-picker catalog. Hiding provider rows in the app may not reduce a client's model count if the client probes `/v1/models` directly. Before claiming cleanup, inspect the actual picker data path and configure a supported client-side allowlist/static model set with discovery disabled when the goal is a curated picker. Verify both layers separately: the upstream catalog may remain large by design, while the picker must contain only the requested models.
7. **Verification:** verify the in-app version, relevant setting, imported item count/status, endpoint health, and that unrelated ports/processes remain unchanged. Report success only from fresh tool output. For model catalogs, perform a fresh picker-level count/list check and one minimal generation canary per retained model; do not treat `/v1/models` count alone as proof that the picker is cleaned.
8. **Account-pool/concurrency boundary:** when investigating a multi-account model proxy, inspect the actual route path before changing settings. A direct model request selects an account before the ordinary per-account semaphore; `maxConcurrent=1` then serializes that selected account and does not, by itself, re-run selection or spill a queued direct request to another account. A combo can implement a distinct pre-dispatch capacity spill path for concrete targets with different pinned `connectionId` values, but do not infer its exact helper or behavior from a version note: inspect the live source/runtime and verify the current implementation. The safe invariant is atomic, non-queueing admission for the priority path; an observation-only `isAccountSemaphoreFull(...)` check races under bursts and can still queue all work behind the first account. Any pre-acquired slot must have an explicit ownership handoff and must be released on every normal early return, thrown error, non-stream completion, and stream finalizer; a passing unit test for the admission primitive alone is not sufficient. Verify strategy, target order, pinned connection IDs, and whether the request is actually called by `combo/<name>`; a direct `provider/model` call will not use this combo fallback. Distinguish fill-first/priority, round-robin, quota/error failover, combo capacity skip, account semaphore, and queue timeout. `queueDepth=0` and `failoverBeforeRetry` are not substitutes for the combo capacity gate. Reproduce with at least two real connections and sanitized selected-connection/decision-trace evidence before claiming busy-aware behavior. Keep account rotation quota/cooldown-driven when the operator wants to avoid request-by-request round-robin.

**Burst-capacity correction:** never treat “five sessions failed” as proof that `maxConcurrent=2` is unsafe, and never treat one successful five/six-request run as proof that `maxConcurrent=2` is universally safe. First determine whether requests were concentrated on one account, rejected by process-wide heavy admission before routing, or rejected upstream after account selection. In the current OmniRoute implementation, the chat route calls the process-wide admission layer before combo/account dispatch; `CHAT_MAX_HEAVY_IN_FLIGHT` and structural `chat_admission_busy` therefore cap heavy requests independently of the number of provider accounts. A combo can only distribute requests that survive that gate. A light combo canary is insufficient: always run a realistic heavy-payload burst through the exact combo name used by the client and record pass/fail counts, latency, sanitized selected-connection evidence, and rejection reasons. Treat the operator’s workload as tool-heavy: one conversational session can issue many model requests through tool rounds, retries, compression, or handoffs, so “number of sessions” is not the same as “number of requests.”

**Pool-operation correction:** configure the account pool once; do not require the operator to assign an account or create a separate request for every session. A client-facing combo alias should contain the same production model on distinct pinned connection targets, and Hermes should call the alias. The pool/router must handle each request, including requests emitted by tool-heavy sessions. Report the distinction explicitly: one user turn may be one request, but a session with tools can generate many requests. Do not claim that request N will reach account C unless C is a real active target and the request passed global admission and reached combo dispatch. Adding a new provider connection does not automatically add it to a combo with pinned `connectionId` steps: update the existing combo target list (or deliberately create a new pool alias), then verify the combo has the expected distinct active targets. Do not tell the operator to manually map sessions to accounts.

**Concurrency-tuning correction:** do not reset every account to `maxConcurrent=1` or `2` solely out of theoretical caution. In heavy workloads where sessions spam multiple tools, artificially low per-account caps cause premature saturation and trigger `503 ALL_TARGETS_SKIPPED`. Follow the operator's sizing principle: set to the highest proven capacity ceiling (e.g. `maxConcurrent=3` per account with matching global `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT=9` for a 3-account pool), and only step down if genuine upstream 429/quota exhaustion occurs.

**Priority account-safety correction:** `priority` alone does not prove the declared pinned-account order is preserved. Two continuity layers can still promote a later account before pool-1: (1) first-message **session stickiness** and (2) rendezvous **prompt-cache affinity** within a single-model account pool. For a safety-first pool that must use `pool-1 → pool-2 → …` and spill only on real capacity/quota/cooldown/error gates, disable both per-combo flags:

```json
{
  "disableSessionStickiness": true,
  "disablePromptCacheAffinity": true
}
```

`disablePromptCacheAffinity` must be supported by the installed source schema/router before setting it through the management API. It prevents account-order re-ranking only; it does **not** delete or strip client/upstream `cachedContent`. After the source update/build/restart, configure through the official combo API, read back the exact flags, and verify one fresh request’s `combo_step_id` ends with its executing `connection_id`. If a later pool is selected after this change, inspect per-connection Gemini quota snapshots and safety-gate logs before treating it as a routing bug: a lower pool with healthy quota is the correct safe spill when earlier pools are exhausted or below quota cutoff. See `references/priority-account-safety.md`.

**Crash vs Throttling Taxonomy:**
- `WinError 10054 / APIConnectionError`: Local socket severed mid-stream because the proxy process was killed/restarted while sessions were active. Not an upstream failure.
- `503 ALL_TARGETS_SKIPPED`: All combo targets reached their configured `maxConcurrent` ceiling simultaneously. Solution: raise per-account `maxConcurrent` and global admission.
- `Priority vs Round-Robin`: Priority routing concentrates traffic on the primary account to exploit prompt caching, spilling over to secondary targets only on concurrency saturation or error. Round-robin rotates blindly on every request, defeating prefix caching.

For a pool of currently usable accounts, configure the pool once rather than assigning accounts to sessions. A combo with the same model pinned to distinct connection IDs can provide native capacity-aware target skipping; for example, three active connections with `maxConcurrent=2` expose up to six per-connection target slots, but only if the process-wide admission ceiling and upstream capacity allow six heavy requests. If the global gate is lower, raising per-account caps cannot help. If all pool targets are full, the combo must either wait through an explicitly configured outer queue/retry policy or return a retryable error; do not claim that the next request will “find account C” unless the pool has a real C target and the request reached combo dispatch.

When a live pool has fewer connections than the operator expects, report the exact `/api/providers` count and active/quota state. Do not infer that “quota 3” means four or five Omni connections; quota availability, stored connection rows, eligible connections, and process admission are separate measurements. See `references/account-pool-concurrency.md`.

**Restart/port pitfall:** before restarting a source-launched local app, inspect both the live PID command line and the repository launcher’s port resolver plus `.env`. A neighboring service may own the default port (for example, a 9Router on `20128`) while the target app normally listens on another port (for example, `20129`). Stop only the target PID, then relaunch with explicit target port variables when the launcher otherwise inherits the conflicting default. Verify the target listener and health endpoint before running canaries. A failed relaunch due to `EADDRINUSE` is not evidence that the app or configuration is broken; correct the port scope and retry.

**Burst-test interpretation:** when a real 5–6-session burst fails, identify the boundary before changing caps. A failure can mean (a) all requests selected one account under direct fill-first routing, (b) the process-wide heavy/structural admission gate rejected requests before account selection, (c) combo capacity skipped all targets, or (d) upstream admission rejected requests after selection. Do not use the count of failed sessions alone to declare `maxConcurrent=2` unsafe. Test both a lightweight burst and a production-shaped heavy burst through the exact combo alias, then inspect sanitized selected-connection logs and rejection reasons. See `references/omniroute-account-pool-burst.md`.
9. **Communication:** use the user's requested language and format. For this user, report in concise Vietnamese with three labels when useful: `Mục tiêu`, `Kết quả`, `Blocker`. Answer the exact requested check first; do not substitute a screenshot description or a generic canary result for the requested root-cause/configuration verification. Do not narrate internal policy or tool mechanics unless they directly block the task.

## Shared OmniRoute: catalog curation and single-account admission control

When multiple Hermes machines share one OmniRoute/OpenAI-compatible proxy, separate two problems:

1. **Picker catalog:** a client may probe `/v1/models` and show hundreds of upstream IDs even when OmniRoute's provider dashboard hides models. To curate the client picker, configure the client/provider with an explicit `models:` allowlist and `discover_models: false`. Verify the picker payload separately from the proxy's upstream catalog count.
2. **Runtime admission:** `HTTP 503 chat_admission_busy` can coexist with successful short canaries. It means the proxy could not admit a request at that moment, commonly because several large sessions share one upstream OAuth account. A successful `/v1/models` call or one short generation is not proof that concurrent large requests are healthy.

For a shared OAuth connection with only one active account:

1. Reproduce with two realistic concurrent requests, not only a one-message probe. Record status, latency, message/tool scale, and response code.
2. Read `/api/providers` and `/api/resilience` before changing anything. Confirm the connection is active/healthy, note whether `maxConcurrent` is unset, and record global queue values.
3. Set the affected connection's `maxConcurrent` to `1` through the official `PUT /api/providers/<connection-id>` endpoint. This serializes requests for that account without throttling unrelated providers. Never edit the runtime SQLite database for this.
4. If logs show local queue expiration (for example a `504` after a short `maxWaitMs`), raise only `requestQueue.maxWaitMs` through the official `PATCH /api/resilience` endpoint, preserving unrelated fields. A longer queue wait prevents false queue failures but does not create upstream capacity.
5. Re-read both endpoints, then run two concurrent canaries. Acceptance is both requests returning `2xx`; the second may take longer because it is correctly queued. Report that latency trade-off.
6. Treat `403 with x-goog-user-project` followed by retry without that header and intermittent `TruncatedStreamError` as secondary transport/provider behavior until a fresh probe proves persistent authentication failure. Do not rotate or delete OAuth credentials based on those messages alone.

**Communication rule:** when the user asks to investigate a live model failure, inspect the live endpoint and logs first. State the exact failing component; do not merely re-describe an attached screenshot or treat an earlier short canary as current proof.

See `references/remote-omni-admission.md` for the focused evidence sequence, error taxonomy, official endpoint payloads, and verification recipe. See `references/omniroute-pool-burst-notes.md` for the consolidated tool-heavy pool-routing and burst-capacity lessons.

## Common pitfalls

- “Update OmniRoute” does not mean “update the TikTok repository.”
- `taskkill` is not an update step; do not add it just because a port exists.
- A successful source build is not proof that the running app was updated; check the runtime version and HTTP endpoint.
- A disabled dashboard password is convenient but removes a local management boundary; mention that trade-off briefly, without blocking an explicitly requested local-only change.
- A proxy workbook may look like ordinary `host:port:user:pass` data while containing secrets. Never print sample rows or copy credentials into chat.
- Browser element references change after navigation; always take a fresh snapshot before clicking a newly rendered control.

## Missing-config recovery for installed local apps

When an installed app is launched through a shortcut or wrapper and fails because its config path is missing:

1. Inspect the shortcut or launcher target, arguments, and working directory first; do not assume the app's default config location.
2. Search the target runtime directory and known backup/sync locations for an existing config. Never overwrite a candidate before making a timestamped backup.
3. If no prior config exists, reconstruct only from the exact installed version's shipped example/template, preserving the app's existing data/auth directory where the format supports it. Do not invent or copy credentials into the new file.
4. Align only the runtime values required by the launcher contract, especially the configured port; remove placeholder/example secrets rather than enabling them.
5. Restart only the target app after the config change and verify the process command line, listening port, root/dashboard endpoint, and logs.
6. Distinguish `service restored` from `accounts/config restored`: a template-based recovery may bring the server up while leaving zero auth/provider entries. Report that as a separate blocker instead of claiming full recovery.

A session-specific recovery transcript and validation pattern is recorded in `references/missing-config-recovery.md`.

For the reusable distinction between an upstream model catalog and a client-side curated picker, see `references/catalog-picker-boundary.md`.

## Runtime supervision and crash recovery

For source-launched Windows apps that must recover after a child process exits, follow `references/runtime-supervisor-and-crash-recovery.md`. Verify the actual listener/PID and health endpoint; do not treat a surviving npm/cmd window as proof of liveness. Prefer production mode, use a mutex-guarded watchdog, and use the user's Startup folder only when Task Scheduler is unavailable or denied. Distinguish verified child-process exit from an unobserved exact exception.

## Verification checklist

- Target URL/port is reachable and identifies the intended app/version.
- Requested setting reflects the new value after reload.
- Import preview/parser reports the expected count and no unexpected parse failures.
- No unrelated application, repository, cron job, lease, or credential store was changed.
- Final response is concise, in the requested language, and distinguishes completed work from blockers.

## CLIProxyAPI management and OAuth validation

For CLIProxyAPI/CPAMC-like local proxy dashboards, keep three credential layers separate:

1. **Management Key** controls `/v0/management/*` and the dashboard. It has no universal default. `remote-management.secret-key: ""` disables the management routes and produces `404`; after configuring a key, unauthenticated requests should produce `401`, while an authenticated request should produce `200`. Never confuse it with a neighboring gateway's dashboard password or an upstream API key.
2. **Client API keys** authenticate `/v1/*`. Never leave `your-api-key-*` values from an example config enabled; remove placeholders rather than treating the endpoint as healthy.
3. **OAuth/auth files** are upstream account state. A running process, a listening port, or a successful `/v1/models` catalog request does not prove that a provider can complete a model request.

For a model smoke test, first verify the actual process/listener port and query `/v1/models`. Select a model returned by that exact instance, then send exactly one minimal `POST /v1/chat/completions` request and record only HTTP status, returned model, finish reason, and a short response prefix. Do not retry-loop or print tokens/account data. Interpret `403 PERMISSION_DENIED` with `VALIDATION_REQUIRED` / `Verify your account to continue` as an upstream OAuth account-verification issue: do not delete, disable, or rewrite the auth file. Preserve the raw upstream JSON and extract `details[].metadata.validation_url` (or the provider-equivalent validation URL) before the proxy reduces the error to a generic 403; have the operator verify in the browser signed into the affected account, then reconnect and perform one fresh smoke test. A connection test, token refresh, quota read, or model catalog response alone does not prove generation is authorized.

When using a screenshot, verify the address bar port against the live listener; `6018`, `60818`, and neighboring gateway ports may be different instances. For the CLIProxyAPI recovery transcript, safe header probes, and Antigravity validation interpretation, see `references/cliproxy-antigravity-recovery.md`.

## Supporting detail

See `references/runtime-app-update-and-import.md` for the reusable OmniRoute-style workflow, UI paths, and credential-safe proxy import handling.
See `references/google-drive-desktop-lost-found.md` for diagnosing and resolving Google Drive for Desktop "Lost and Found" (`Bị thất lạc và đã tìm thấy`) sync conflicts and notifications.
See `references/gpm-antidetect-local-api-and-proxy-mapping.md` for GPMLogin local REST API endpoints (port 19995, `/api/v3/profiles`), payload specifications (`profile_name`, `raw_proxy`), profile preservation rules, and 5:1 multi-account proxy pool batching.
