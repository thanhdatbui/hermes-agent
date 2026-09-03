# Priority account safety: OmniRoute-style single-model pools

## Problem signature

A combo declares pinned targets in priority order, but live call logs keep showing a later account while earlier provider rows still appear `active` and below `maxConcurrent`.

Do not assume `priority` is broken. First distinguish:

1. **Pre-order re-ranking:** session stickiness or prompt-cache affinity moved a later account to index 0.
2. **Safe pre-dispatch skip:** earlier accounts were not called because their quota/cooldown/credential/capacity gate blocked them.
3. **Credential remap:** combo step says account A but execution used B. This is a binding invariant failure, distinct from either case above.

## Safe desired routing policy

```text
pool-1 → pool-2 → … → pool-N → Starter last
```

A request moves forward only when the current target has a real safety reason:

- exact account has no free `maxConcurrent` slot;
- account/model quota exhausted or below operator cutoff;
- 429, 403, cooldown, model lock, or credential gate;
- exact hard binding cannot obtain its own credential.

Do not replace this with request-by-request round-robin when account safety and natural continuity matter.

## Two separate order-overriders

### Session stickiness

Often keyed from the first user message and held in memory (commonly a 15-minute TTL). It can keep promoting the prior account for a session even though strategy is priority.

### Prompt-cache affinity

Rendezvous hashing can rank an account that is cache-local ahead of other targets. In a pool where every target is the *same model* but each has a different `connectionId`, model-scoped affinity still reorders the account group.

## Conservative per-combo configuration

For a priority account pool, preserve source/client cache data but stop cache and session routing from changing account order:

```json
{
  "strategy": "priority",
  "config": {
    "maxRetries": 0,
    "failoverBeforeRetry": true,
    "maxSetRetries": 0,
    "disableSessionStickiness": true,
    "disablePromptCacheAffinity": true
  }
}
```

`disablePromptCacheAffinity` is a source/runtime capability, not a generic OpenAI field. Add schema + routing support, build/restart, then apply it through the official combo API and read it back. Never write the runtime SQLite database directly.

## Evidence sequence

1. Capture the combo: strategy, ordered target IDs, pinned `connectionId`s, per-account caps.
2. Capture recent calls with timestamp, status, `combo_step_id`, `connection_id`, correlation id and error summary.
3. Assert binding for executed calls:

```text
combo_step_id endsWith(connection_id)
```

4. For each skipped earlier connection, read the **freshest** model-window quota snapshot, cooldown/lock state, and capacity. Provider row `active` alone is insufficient.
5. Classify result:
   - later account with `200`, earlier account exhausted → correct safe spill;
   - later account with no documented safety gate → investigate order-overriders;
   - target/account mismatch → fail closed before upstream and repair credential binding.

## Operational cautions

- Do not lower `maxConcurrent` as a substitute for removing pre-order re-ranking. A cap changes only behavior once reached.
- A run of 200s does not establish account-policy safety. Measure request cadence, tool-driven fan-out, cache-hit ratio, quota drain, and upstream 429/403 trends separately.
- Do not report all current traffic on one account as a routing fault until quota snapshots are checked; a healthy late pool may correctly carry load after earlier quotas are depleted.
