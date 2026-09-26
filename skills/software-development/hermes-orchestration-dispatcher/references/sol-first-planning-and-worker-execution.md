# Sol-first planning and worker execution

## Trigger
Use this contract when the user requires Sol to plan and other agents to execute.

## Required flow
1. Coordinator gathers only the minimum evidence and closes the task scope.
2. Call the configured GPT-5.6 Sol Planner before the coordinator writes a plan.
3. On successful Sol output, preserve the returned `SOL_PLAN_ID` and relay `SOL_PLAN_SOURCE: SOL_PLANNER`.
4. Dispatch a worker with the Sol plan, exact allowlist, acceptance command, and execution-only instructions.
5. Worker must not self-plan, delegate, expand scope, or replace the Sol contract.
6. Coordinator independently checks changed files, diff, and focused verification.

## Fallback rule
Coordinator planning is allowed only after real, auditable Sol timeout/error/refusal evidence. A worker timeout, ambiguous result, or missing verification is not proof that Sol failed. Record the exact reason and authorization before fallback.

## Guard implementation lessons
- A gate that requires `SOL_PLAN_SOURCE: SOL_PLANNER` must make the auto-generated Sol retry message emit both source and plan ID; otherwise legitimate retries are rejected.
- A stdin executable hook is not a pytest module. Verify it with `py_compile` and deterministic subprocess/stdin cases; do not add pytest compatibility merely to satisfy an invalid test target.
- After changing policy text, search for stale contradictory phrases such as coordinator/flash-first planning and remove them through a separate exact policy contract.
- For CRLF policy files, verify CRLF counts and lone LF/CR counts after editing.

## Evidence checklist
Record: Sol model/plan ID, exact target files, anchor uniqueness, worker model, files modified, focused command and exit code, and any fallback evidence. Never accept a worker self-report without independent verification.
