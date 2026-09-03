# OmniRoute multi-account burst verification

Use this reference when several Hermes sessions share one OmniRoute/Antigravity listener and the operator wants the pool to absorb a burst without manually assigning accounts.

## Model of the system

There are separate capacity boundaries:

1. **Process-wide chat admission** runs before account selection. Its heavy/structural limits are boot-time controls (`OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT`, `OMNIROUTE_CHAT_ADMISSION_QUEUE_MS`). More OAuth connections do not raise this limit automatically.
2. **Account selection** chooses a provider connection. Direct model requests commonly follow provider strategy/priority and may concentrate on one account.
3. **Combo target capacity** can be account-aware. A combo can contain the same model as multiple structured targets with distinct `connectionId` values. In the v3.8.50 combo path, a full pinned connection is pre-checked with `isAccountSemaphoreFull(...)`, recorded as `concurrency_cap`, skipped, and the loop continues to the next target.
4. **Upstream admission** may still reject a request after it reaches an account; this is distinct from local `chat_admission_busy` and from combo target skipping.

## Safe pool shape

For N currently usable connections and a burst capacity of K, configure the pool once:

- one combo alias;
- the same production model on each target;
- each target pinned to a different `connectionId`;
- `priority` or `fill-first` when deterministic preference is wanted;
- do not set `fallbackOnlyOnQuotaExhaustion` for capacity spillover;
- set each connection's `maxConcurrent` deliberately;
- call the combo name from the client (`combo/<name>` or the exact combo model name), not the raw provider/model ID.

The nominal pool ceiling is `N × per-account maxConcurrent`, but this is not a guarantee. The process-wide admission ceiling, queued-byte budget, upstream limits, quota/cooldown state, and request size can all reduce usable capacity.

## Verification recipe

1. Read `/api/providers` and record only sanitized fields: connection ID prefix, provider, active/test status, priority, `maxConcurrent`, cooldown/error state. Confirm the number of active connections matches the operator's expectation.
2. Read `/api/combos` and verify the combo name, strategy, active state, model count, and distinct pinned connection IDs. Do not print credentials.
3. Run a lightweight concurrent burst through `/v1/chat/completions` using the combo name. Record count, HTTP statuses, wall time, and response prefixes only.
4. Run a production-shaped heavy burst (message/tool count and approximate token size similar to the real workload). A lightweight pass does not validate heavy admission.
5. If heavy requests fail, classify the boundary from the response: `structure_limit`/`chat_admission_busy` means local admission before combo routing; `concurrency_cap`/all-targets-skipped means combo capacity; upstream 429/503 means provider-side behavior after routing.
6. Inspect sanitized Omni logs for selected connection ID prefixes and confirm whether multiple pool targets were actually selected. Do not infer account distribution from HTTP success alone.
7. After a restart, verify the intended listener with `/api/monitoring/health`, `/api/providers`, `/api/combos`, and the port owner. Preserve neighboring listeners such as 9Router.

## Interpretation example

With three active Antigravity connections and `maxConcurrent=2` each, a six-request burst can be attempted as a six-slot pool. If the process-wide heavy admission is still two, only roughly two heavy requests can enter and the remainder may be rejected before routing. After raising the boot-time admission ceiling to six and restarting the target listener, a six-request heavy canary that returns six `2xx` responses is evidence that the local gate and this workload shape allowed the burst; it is not a universal guarantee for larger prompts, longer runs, or changed upstream quota.

## Restart pitfall

A source checkout may contain `.env` with `PORT=20128` even though the target OmniRoute instance is meant to listen on `20129` and 9Router already owns `20128`. Before relaunching, inspect the old PID command line and `scripts/build/runtime-env.mjs`; stop only the target PID and explicitly pass `PORT`, `API_PORT`, `DASHBOARD_PORT`, and `OMNIROUTE_PORT` for the target listener. Verify health before testing. A relaunch that exits with `EADDRINUSE` indicates a port-scope mistake, not proof that the application failed its configuration.
