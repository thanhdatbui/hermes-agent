# Coordinator anti-stall and alert identity

## Lessons
- When the user explicitly orders fix/recover/finish, continue the bounded execution ladder: evidence -> exact patch -> focused test -> target-scoped canary -> report. Do not stop after inspection.
- Stale test fixtures are valid targets when the failure is proven to be fixture drift. Fix them and rerun the focused test; do not preserve stale mocks as a blocker.
- Explicit user authorization permits a shared/cross-repository fix with an exact allowlist. A consumer-repo boundary is not an absolute blocker.
- Worker timeout is transient: retry the same bounded contract before structural escalation. Missing live evidence does not block offline code/test work; report live verification separately as PARTIAL.
- DONE requires independently verified diff, focused test output, and live canary when the task targets a device. BLOCKED requires a concrete command/exit code/log/error or an unresolved irreversible/business decision.

## Alert identity contract
Every per-machine or batch alert must preserve `machine`, workbook `row`, `source_row`/`slot`, username/account, serial, artifact directory, log path, and correlation/run ID from per-machine result through batch aggregation to the formatter. If genuinely unavailable, emit `UNKNOWN`; never use row 1, another account, or a fake `latest` path. A machine number alone is insufficient to select a canary when multiple accounts share that machine.
