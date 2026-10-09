# Live canary vs offline verification boundary

## Durable lesson

For browser/GPM recovery work, distinguish three evidence classes:

1. **Offline/mock verification** — pytest with mocked Playwright, ADB, HTTP, or workbook boundaries. This proves code behavior only.
2. **Dispatch evidence** — a cron run returning success, a worker completion summary, or an active background PID. This proves launch/dispatch only.
3. **Live canary evidence** — a target-bound run with the exact email/profile, fresh GPM/OmniRoute preflight, real runner stdout/stderr, a fresh target-matching browser screenshot/artifact, and a post-run validation state.

Never relabel class 1 or 2 as class 3. `ACTIVE=True`, `last_status=ok`, or a healthy cron telemetry snapshot may predate the attempted run and is not proof of relogin.

## Single-target gate

Before running a production watchdog as a canary, inspect its entrypoint. If it has no `argparse`/single-target selector, running it directly scans the whole pool and is not a single-account canary. Use an existing target-scoped driver or a low-level function imported by a temporary harness; do not edit a production profile list merely to force a one-account run.

Bind the run to the current GPM profile ID and OmniRoute connection ID, preserve the literal command and timestamp, and require a fresh screenshot or artifact path. If the artifact is absent, stale, mismatched, or not inspected, report `UNPROVEN`.

## Reporting vocabulary

- `PASS`: live target evidence and post-condition both verified.
- `FAILED`: live target run executed and returned a concrete failure with matching evidence.
- `UNPROVEN`: only mocks, dispatch status, pre-existing service state, or missing/stale artifacts exist.
- `BLOCKED`: the approved execution path is prevented by a real permission/tool/lock blocker; include the exact evidence.

A worker's self-report is not evidence until the Coordinator verifies the physical artifact path and binds it to the target. Keep screenshots from different components separate: a phone/S7 screenshot cannot prove a PC GPM browser recovery.

## Reference

See `references/live-canary-vs-offline-verification.md` for the session-derived checklist and failure examples.
