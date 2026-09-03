# Review routing and ISO log-query discipline

## Reviewer selection

- For concurrency/routing reviews, use the user's configured 9Router review combo such as `plan-review-hard` through `:20128`.
- Do not substitute a bare model call or Claude Sonnet. If the user explicitly demands a direct reviewer, use only GPT-Sol or Claude Opus CLI.
- State read-only scope and prohibit source/runtime/config/account mutation before the call.
- A shell quoting failure or client timeout is not a review result. Repair the invocation wrapper, preserve read-only scope, and let the requested review complete unless the user stops it.

## Correct time-window queries

OmniRoute `call_logs.timestamp` uses ISO UTC such as `YYYY-MM-DDTHH:MM:SSZ`. SQLite `datetime()` emits a space separator. Lexical comparison between the two formats can include old incidents while claiming a recent window.

Compute cutoff in the caller, serialize to ISO UTC with `T` and `Z`, and bind it as a query parameter. Example principle:

```text
latest = max(timestamp)
cutoff = ISO_UTC(parse(latest) - 10 minutes)
WHERE timestamp >= :cutoff
```

## Pool diagnosis sequence

1. Count recent results by `status` and target step.
2. Check binding only on calls with both values:
   `substr(combo_step_id, -36) = connection_id`.
3. Inspect live `/api/admin/concurrency`: `running`, `queued`, and `maxConcurrency`.
4. Separate target-local upstream `403`/`429` attempts from final request outcomes.
5. Interpret `priority` as first-eligible ordered spillover, not round-robin.

A high total request count on one target does not prove saturation. If `running` stays below cap and traffic is sequential, lowering `maxConcurrent` does not rebalance it; investigate session stickiness/continuity target reordering first.

## Cache trade-off

Gemini `cachedContent` is client-provided and can be scoped to the account/project that created it. Preserve explicit cache references. Generic session stickiness should not pin a shared priority pool unless the combo intentionally prioritizes cache continuity over distribution. Exact target → credential binding must remain intact regardless of cache behavior.
