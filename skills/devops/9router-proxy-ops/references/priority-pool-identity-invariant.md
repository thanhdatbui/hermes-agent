# OmniRoute priority-pool identity invariant

## Invariant
For a priority target with connection `X`:

```text
combo target X = auth-selected credential X = executor connection X = semaphore key X
```

If `X` is full, excluded, cooldowned, or yields an account-local 403/429, the current target must fail and `combo.ts` must advance explicitly to target `Y`. Never clear a hard-bound `X` and choose arbitrary sibling `Z` within the same target attempt.

## Diagnosis
1. Read `call_logs` after a known restart/canary window.
2. Extract the connection UUID suffix from `combo_step_id`; compare it with `connection_id`.
3. A `200` is not sufficient proof: a `200` with mismatched IDs means silent remap and cap bypass.
4. Distinguish an upstream `429` from `Semaphore timeout ...`: the latter is local queue pressure. Increasing semaphore timeouts prolongs hangs and does not fix concentration.

## Regression tests
Create focused tests for:
- target `X` selected while sibling `Z` is preferred: selected credential remains `X`;
- hard-bound `X` excluded: auth does not return `Z`;
- `X` full / `Y` available: combo progression is exactly `X → Y`, not `Z`;
- executor sees hard target `X` with credentials `Z`: reject before upstream call.

## Fix shape
Scope hard binding to priority targets with a concrete connection ID. Preserve soft fallback behavior for other routes. At auth selection, hard-bound failure returns target-local no-credential/unavailable rather than sibling selection. Keep an executor-boundary assertion as fail-closed defense.

## Review policy
For this class of routing/concurrency audit, call the configured 9Router combo `plan-review-hard` using `tools: []`, `tool_choice: "none"`, and `stream: false`. Do not use Claude Sonnet as reviewer and do not bypass configured review combos with bare model calls. Use a Python request launcher rather than nested shell quoting for long review payloads.
