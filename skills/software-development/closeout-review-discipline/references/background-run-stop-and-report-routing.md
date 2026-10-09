# Background-run stop, report routing, and closeout evidence

## Reusable pattern

When a user narrows or reverses an automation request, treat the newest message as a replacement contract:

1. Stop matching worker processes and verify no matching process remains.
2. Inspect scheduler metadata for the exact job; unrelated jobs are not part of the stop action.
3. Keep reports on the requested destination. A report written to a local cron-output directory is not proof that it should be delivered to the origin chat.
4. For a completed background command, distinguish `TERMINATED` from business `SUCCESS`; inspect structured output, artifacts, and post-state.
5. For closeout, bind the gate to the actual candidate. If the target has no diff, report `NO_CANDIDATE_DIFF`; if the repository has unrelated dirty work, use semantic `--files` lanes and preserve the rest.

## Evidence labels

- `STOPPED_VERIFIED`: matching process/scheduler path is stopped and rechecked.
- `REPORT_ROUTE_VERIFIED`: exact cron `deliver`, `script`, `no_agent`, and schedule were inspected after correction.
- `PROCESS_TERMINATED_ONLY`: exit code confirms the process ended, but not the requested business result.
- `NO_CANDIDATE_DIFF`: scoped closeout has no staged, worktree, or committed change for the named target.
- `CLOSEOUT_APPROVED`: reviewer returned `APPROVED`, score >=85, and gate exit code 0 for the same candidate scope.

Do not convert one label into another without the corresponding evidence.
