# Mailbox-only canonical run boundary

## Lesson

A user may request only: “read the newest TikTok mailbox message for devices already at the OTP screen.” That is not a normal registration success task. `--resume --ss --defer-tracking-write` by itself does **not** prove a mailbox-only boundary: a run can resume from Gmail/Chrome or an already-authenticated TikTok state, skip mailbox classification, continue through `[8b]`, `[9]`, `[10]`, navigate to Profile, and emit `SUCCESS` plus a deferred tracking JSON.

## Required evidence contract

For each target, the run-specific canonical log/artifact must contain all of:

1. newest TikTok message selection evidence (freshness/order or canonical newest-row marker),
2. semantic classification: one of `signup completion link`, `login OTP`, or `signup OTP`,
3. redacted code/link evidence where applicable,
4. a stop/return marker at the mailbox boundary.

The following are **not** sufficient:

- `package=gmail` or `package=chrome`,
- `kiem_tra_email=N`, `gui_lai_ma=N`, or `password=N`,
- a later `[login-success]`, Profile screenshot, `tracking_result_*.json`, or `SUCCESS`,
- stale entries from the global `social_reg_log.txt` or old artifacts.

If the canonical implementation does not expose a mailbox-only stop/classification artifact, do not improvise a probe. Report `CLASSIFICATION_NOT_OBSERVED` and the exact later state reached.

## Safe run procedure

1. Perform normal preflight: exact inventory serial, `tun0`, portrait, no `social_reg`/`_run_all_targets` worker, and lock owner liveness.
2. Reclaim retained locks only through the canonical lock API with explicit full-scope authorization after proving the owner PID is dead. Never delete lock JSON manually.
3. Redirect the exact canonical command to a file, preserving the worker exit code. Never pipe the live process through `tail`.
4. Use only artifacts produced by that run. Redact passwords, OTP digits, tokens, and verification URLs in reports.
5. Stop at the canonical mailbox classification boundary. If the flow crosses into login/profile/registration, stop as soon as observed and report the exact state; do not call that a mailbox classification.
6. After any early stop, verify the worker is gone and inspect/reconcile both machine and serial lock leases before another target.

## Reporting template

- `STT/serial`: exit or explicit early-stop status
- `canonical log`: exact run-specific path
- `artifact`: exact run-specific path, if present
- `classification evidence`: quoted redacted canonical lines, or `CLASSIFICATION_NOT_OBSERVED`
- `newest message`: `signup-completion` / `login OTP` / `signup OTP` / `unknown`
- `side effect state`: exact TikTok UI state if the flow crossed the requested boundary
- `tracking`: confirm deferred/no workbook write only when backed by run output and file checks
