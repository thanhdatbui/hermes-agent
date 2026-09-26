# Sol-first planning gate

## Trigger
Use this for Taadaa work requiring decomposition, implementation planning, patch contracts, architecture decisions, or worker dispatch.

## Required lifecycle

```text
request → coordinator gathers narrow evidence → Sol planner → SOL_PLAN_ID
        → coordinator validates scope/schema → execution-only worker
        → focused verification → canary if explicitly required → DONE/BLOCKED
```

## Rules

1. Call `D:\Taadaa\tools\sol_planner.py` before the coordinator creates the primary plan or dispatches an implementation worker.
2. On success, preserve the returned `SOL_PLAN_ID`. Coordinator may validate, but must not replace Sol's design with an independently invented plan.
3. Worker prompt must explicitly prohibit new planning, delegation, and scope expansion. Missing, contradictory, or insufficient Sol plan means stop and return `BLOCKED` with the exact gap.
4. Coordinator planning is allowed only after a real Sol failure: timeout, transport/provider error, refusal, or invalid planner output. Record machine-readable evidence first. Missing ID alone is not evidence of Sol failure.
5. The dispatch boundary should expose states such as `SOL_PLAN_REQUIRED`, `SOL_PLAN_VALIDATED`, and an explicitly authorized fallback state. A post-hoc Sol check after coordinator planning is not equivalent to Sol-first.

## Evidence checklist

Record the Sol route/model, timestamp or request correlation, exit/status, error or invalid-output reason, plan ID when successful, and the exact fallback reason when fallback is used.

## Session finding
The previous guard had a Sol hook only in a narrow code-edit path. That is a Sol gate, not a global Sol-first lifecycle; policy text must not continue to say the coordinator is the normal primary planner when this workflow is enabled.
