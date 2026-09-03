# Explicit single-machine recovery ladder

Use this reference when an operator explicitly authorizes a materially different,
evidence-backed recovery of one TikTok machine after a normal batch omitted
later recovery stages.

## Preconditions

- Read the newest target `report.json` first. Confirm the post state is safe to
  retry (`post_submission_state` is `null` when the prior run never submitted)
and record `status`, `last_state`, `reason/signature`, and `post_verified`.
- Validate both exact aliases: `machine_<N>.lock.json` and
  `serial_<serial>.lock.json`. They must agree on machine, serial, project,
host, PID, and lock ownership fields.
- On Windows, prove the recorded PID is dead with:
  `tasklist /FI "PID eq <pid>" /NH`.
- Scan replacement workers by actual process metadata. A Python executable with
  `-m tiktok_workflow --machine <N>` is a live competitor; a bash/terminal
  wrapper whose command text merely contains those strings is not.
- Only after all guards pass, copy exactly the two matching stale aliases into a
  timestamped backup/evidence directory and remove exactly those two originals.
  Never use a broad lock glob or kill a foreign process.

## Direct worker contract

Run exactly one background worker for the target, with the template config
rebinding through `--machine`:

```bash
echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" \
  "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
  -m tiktok_workflow \
  --config "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" \
  --machine <N> --no-dry-run --recovery-mode \
  --allow-device-reboot-recovery \
  > /d/CodexRuntime/tiktok-video/recovery-m<N>-full-ladder-<timestamp>.log 2>&1; \
  echo WORKER_EXIT=$?
```

Use a background process with completion notification and wait until it exits.
Do not replace the worker's recovery handler with manual ADB taps, Back, reboot,
coordinate taps, or Xiaowei UI operations.

## Evidence interpretation

Separate **authorization** from **execution**. The allow flag means the state
machine may use the bounded soft-reboot/coordinate handlers; it does not prove
those handlers ran. Read the log and list the stages actually present:

1. ATX kill (if the handler logs it)
2. force-stop/relaunch attempt 1
3. force-stop/relaunch attempt 2
4. bounded soft reboot and post-reboot verifier
5. evidence-gated coordinate fallback after the ladder is exhausted

If the workflow reaches a new failure before a later stage—for example,
`UI_DUMP_FAILED` in `DISMISS_POPUPS` after feed visual confirmation—report the
missing stages and stop fail-closed. Do not infer that a stage was skipped by
platform blocking unless the log contains the precise platform error.

Final verdict is report/verifier-driven:

- SUCCESS only with `status=SUCCESS` and `post_verified=true` (plus the
  accepted/verified post state required by the consumer contract).
- `WORKER_EXIT=0` or a successful shell wrapper is not completion proof.
- On `MANUAL_REVIEW`/blocked outcome, read the final lock aliases. A post-run
  `handoff` lock with `owner_active=false` and a dead PID is retained for the
  next authorized recovery; do not delete it merely to clean up.

## Evidence from the 2026-08-10 m35 run

The explicit worker proved template rebinding and ran in recovery mode, but the
log showed only `Force-stop + relaunch 1/2`, then feed visual confirmation, then
`UI_DUMP_FAILED` in `DISMISS_POPUPS`. No ATX-kill, second relaunch, soft reboot,
or coordinate-fallback line appeared. The correct result was `MANUAL_REVIEW`,
`post_submission_state=null`, `post_verified=false`, with both post-run lock
aliases retained in `handoff`.
