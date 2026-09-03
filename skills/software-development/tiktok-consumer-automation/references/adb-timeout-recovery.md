# ADB timeout recovery pattern

## Incident signature
`adb command timed out` means the bounded ADB subprocess exceeded its execution deadline. It may indicate a stuck ADB/device transport; it does not by itself prove a TikTok UI or ad-screen cause.

## Recovery matrix

1. Retry the same command a small, explicit number of times (normally 2–3). Keep command timeout bounded; increasing the wait alone can prolong a stuck worker.
2. If the timeout/transport signature persists, soft-reboot only the affected serial, and only with explicit recovery authorization, verified target lock/lease, and opt-in configuration.
3. Permit at most one reboot per recovery window. After reboot wait for `wait-for-device`, `sys.boot_completed=1`, and a read-only ADB probe.
4. Retry the original command once after verified readiness.
5. On failure, preserve the target lock/scene and emit evidence/`FINAL_BLOCKED`; never reboot-loop, restart the ADB server, `pm clear`, or rerun the whole batch.

## Implementation seam

In shared `AdbClient`, `TimeoutExpired` must not bypass bounded retry/recovery policy. Keep reboot disabled by default (`allow_device_reboot_recovery=False`) and let a target-scoped consumer/recovery handler opt in. Reuse the existing soft-reboot/readiness primitive instead of implementing a second scheduler-owned retry loop.

## Regression tests

Cover: timeout retries boundedly; ordinary app-level failure does not reboot; opt-in is required; reboot occurs at most once; readiness gates precede post-reboot retry; persistent failure terminates without an unbounded loop. Validate offline with mocked subprocess/device responses; do not run live ADB as a code-test verifier.

## Operator lesson

A probe-only check is not the requested fix when the operator explicitly asks for reboot. Execute the bounded action on the named serial, then verify. Do not report completion because a later probe happened to pass; completion requires the requested action plus fresh evidence.