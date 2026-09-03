---
name: llm-account-pool-routing
description: Safely diagnose and operate multi-account LLM priority pools without unsafe account churn or misleading routing conclusions.
version: 1.0.0
---

# LLM Account Pool Routing

## Use when

Use for a multi-account LLM/OAuth pool where the operator prioritizes account safety over even distribution, especially when requests unexpectedly concentrate on one account, spill to another, or show `429`/quota behavior.

## Core routing policy

For safety-first pools, preserve this default unless the user explicitly asks otherwise:

```text
explicit priority order
+ exact target-to-credential binding
+ per-account maxConcurrent cap
+ fail-fast spillover on full/cooldown/quota/upstream failure
+ starter/free accounts last
```

Do **not** switch a safety-first OAuth pool to round-robin merely to distribute requests. Round-robin changes accounts frequently and is not the correct remedy for a priority-routing defect.

## Router Topology Disambiguation

Always verify which router is the subject before inspecting logs or SQLite tables:
- **9Router (`:20128`)**: `%APPDATA%\9router\db\data.sqlite` (or `9router.db`), Node app in `%APPDATA%\npm\node_modules\9router\app`.
- **OmniRoute (`:20129`)**: `C:\Users\Kibe\.omniroute\storage.sqlite` (legacy directory priority over `%APPDATA%\omniroute`), Next.js app in `C:\Users\Kibe\OmniRoute`.

See `9router-proxy-ops/references/omniroute-vs-9router-diagnostics-and-proxy-routing.md` for full schema and script recipes.

## Diagnose before changing caps or strategy

1. **Set the scope in plain Vietnamese before mutating:** state the goal, exact config/source scope, explicit non-actions, acceptance evidence, and stop condition.
2. **Use a time-correct query window.** SQLite `datetime()` strings use a space separator while application logs may use ISO `T...Z`; normalize both bounds to ISO before lexical timestamp comparison. Never call a broad history result “last 10 minutes” without validating the cutoff.
3. **Separate three observations:**
   - selected combo target/step;
   - actual credential/connection used at executor boundary;
   - final request outcome after all fallback attempts.
4. **Treat `target != connection` on a `200` as a binding defect.** A `409` fail-closed mismatch means upstream was protected, not that the account was safely used.
5. **Before reducing `maxConcurrent`, inspect live `running`, `queued`, and cap.** Lowering a cap only causes earlier spill when it is actually reached; it cannot fix routing reordering or pre-dispatch eligibility skips.
6. **For an apparently skipped priority account, inspect in order:** quota snapshot for the requested model/window, persisted cooldown, terminal credential status, model lock, credential gate, account semaphore capacity, then request compatibility. `active` alone does not mean eligible.
7. **Do not infer a reordering bug from the final `call_logs` row alone.** Earlier targets skipped before dispatch often have no call-log row. Use decision/trace logs or the per-account quota state to distinguish safe skips from reordering.

## Cache and affinity rules

Keep these concepts separate:

- **Upstream/client cache payload** (for example Gemini `cachedContent`) is independent of router ordering.
- **Session stickiness** can pin a conversation to a previously successful account.
- **Prompt-cache affinity** can reorder accounts by rendezvous hashing even under a declared priority strategy.

For an explicit safety-first priority account pool, any feature that may reorder accounts must be opt-in and independently controllable. If enabled affinity overrides account priority, add a per-combo opt-out rather than disabling cache behavior globally.

A valid safety configuration can be:

```json
{
  "disableSessionStickiness": true,
  "disablePromptCacheAffinity": true
}
```

This preserves the upstream cache payload while preventing router-level affinity from moving a later account ahead of declared priority. Use only after a regression test proves the original reorder.

## Safe implementation workflow

1. Write a focused RED test proving a later account can incorrectly jump ahead of an explicit priority account.
2. Implement the smallest per-combo control; default behavior for unrelated combos must remain unchanged.
3. Validate schema/API persistence for the new config field.
4. Run focused routing/binding tests, typecheck, diff check, build, controlled restart, health check, and one low-impact canary.
5. Verify live evidence:
   - combo strategy and relevant flags read back from API;
   - target/account exact match for successful attempts;
   - no new `409` binding mismatch;
   - skips correspond to actual quota/cooldown/cap state.
6. Do not claim long-term stability from a short window. Report the window length, count, errors, rate, latency, queue/cap, and any uncertainty.

## Communication rules

- Lead with the conclusion in everyday Vietnamese, then the evidence.
- Explain tool interruptions or command errors plainly: whether the operation ran, did not run, or is unknown.
- Do not expose account identifiers, OAuth tokens, raw credentials, or private request content in reports.
- Never describe a workload as “normal user-like” or claim that Google/provider anti-abuse systems will not notice it. State only measured request rate, concurrency, token volume, cache behavior, and provider responses.
- For external/admin-facing reports, state phenomenon and error code only unless the user asks for remediation.

## Pitfalls

- `maxConcurrent` is a capacity ceiling, not a load balancer.
- `200` means the request completed, not that traffic shape is account-safe.
- High request frequency, sub-second inter-arrivals, and very large prompt sizes can be operationally successful while still not resembling manual chat usage.
- A low remaining quota such as `<1%` should be treated as safety-sensitive even when not yet marked exhausted.
- Do not manually alter account/token/quota records to make a priority test pass.
- **Proxy Auth for MikroTik in OmniRoute:** `mirotik1.taadaa.click:10001..10035` requires auth `admin@1:admin@1`. If empty in `proxy_registry`, background token refresh fails with `fetch failed` / `503`, making accounts show red (`Token expired`) even if proxy is live.
- **Antigravity Project ID Binding:** `formatProviderCredentials` in `tokenRefresh.ts` must return `projectId` and `providerSpecificData`. Omission drops GCP project context, causing `422: Missing Google projectId` on model execution.
- **Nested Combos Expansion (`combo-ref` vs `model`):** When nesting a multi-account pool combo inside another combo (e.g., `ag-gemini-pool-3` inside `ag-worker`), it MUST be stored as `{"kind": "combo-ref", "comboName": "ag-gemini-pool-3"}` and NOT `{"kind": "model", "model": "combo/ag-gemini-pool-3", "providerId": "combo"}`. If configured as `kind: "model"`, OmniRoute treats the entire pool as a single step and fails over to the next tier (e.g. Sonnet/fallback models) on the first account glitch instead of unrolling and rotating through all accounts in the pool.
