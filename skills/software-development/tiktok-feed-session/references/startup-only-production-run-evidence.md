# Production startup-only run evidence

Use this reference for a **single-target production startup-only** run after a detector fix. It is a bounded Feed verification, not a follow session.

## Preflight

- Reuse the repository's canonical startup-only entrypoint. Do not make a temporary launcher or substitute a full follow/feed batch.
- Bind both machine number and serial in the plan; print/redact `startup_only=true`.
- Check exactly both lock aliases for the target: `machine_<N>.lock.json` and `serial_<SERIAL>.lock.json`. An active, foreign, blocked, retained, or unverifiable lock is a terminal `SKIPPED_LOCKED`; never force-delete or reclaim it.
- Parse competing process metadata by record. Require the same real Python process record to contain the consumer module and an exact machine token (`--machine 1` must not match `--machine 10`). Do not use aggregate stdout substring checks.
- Verify ADB state and model before device action.

## One live invocation

After preflight passes, invoke the canonical startup-only command exactly once. It may prepare/unlock the device and launch TikTok according to its documented startup contract, but must not switch accounts, load business-account state, navigate follower lists, scroll for candidates, or invoke Follow. Do not rerun just because startup failed or a detector previously skipped the target.

## Success contract

Only report `VERIFIED_FEED` when all of these are independently true:

1. The emitted result is bound to the requested machine/serial and has `startup_only=true`.
2. TikTok is the verified foreground package/activity and the UI dump contains semantic Feed proof.
3. `followed=[]` (or equivalent explicit no-follow evidence).
4. All three artifacts exist and are readable: PNG screenshot, XML UI dump, and JSON evidence.

Exit code, `OPEN_TIKTOK` text, or a process ending is not proof.

## Failure and postcheck

If startup fails after acquiring a device lease, do not manually release or delete locks. Perform a read-only postcheck of both aliases, owner lease/PID, exact target process, ADB, and the canonical artifact root. If release/handoff itself fails (for example an unsupported failure status), report `MANUAL_REVIEW`/`LIVE_BLOCKED` with the precise release error and retained-lock state. A dead owner PID does not authorize manual cleanup in this run; preserve the evidence for the guarded recovery/reaper path. If no verified Feed artifacts were emitted, explicitly report the missing PNG/XML/JSON paths rather than implying success.

## Reporting template

Report: canonical script/config; machine and redacted serial; preflight lock aliases; exact process result; ADB state/model; one invocation and exit code; `FOLLOW_PLAN`; `FOLLOW_RESULT`; `followed=[]`; artifact paths plus existence/readability; final lock aliases/owner state; and whether a screenshot can actually be sent. Distinguish `VERIFIED_FEED`, `SKIPPED_LOCKED`, `MANUAL_REVIEW`, and `LIVE_BLOCKED`.
