# Live recovery preflight and evidence checklist

This reference captures the reusable orchestration pattern for an authorized TikTok upload recovery. It is intentionally class-level; replace the target allowlist and timestamp per run.

## 1. Preflight before any device action

1. Confirm the user supplied explicit live-recovery authorization and an exact target allowlist. Do not ask again when the authorization is already explicit.
2. Fresh-check that no batch, workflow worker, scheduler, or replacement worker is active for the target scope.
3. Read the latest report for every target. Record `status`, `post_submission_state`, `post_verified`, `last_state`, `reason`, and the exact failure signature. Do not trust an old handoff summary over the current report. If fields disagree (for example `post_submission_state=ACCEPTED` while status remains `MANUAL_REVIEW`), record the anomaly and defer to the current verifier.
4. Never use worker exit code as success evidence.

## 2. Stale lock reclaim, narrowly scoped

For each target, inspect exactly both aliases:

- `machine_<N>.lock.json`
- `serial_<serial-from-machine-alias>.lock.json`

Reclaim only when both aliases agree on machine/serial identity, project `tiktok-upload`, status `handoff`, `owner_active=false`, PID and `lock_id`, and the owning PID is dead. Also verify there is no replacement worker between the check and archive. Copy both aliases to a timestamped backup, write an evidence manifest containing the checks and paths, then remove/release only those two aliases. Preserve all foreign locks, including other consumers and explicitly excluded machines. Never perform broad stale-lock cleanup.

## 3. Launch topology

Use one independent background process per target, not a shell loop and not a normal launcher path that omits recovery authorization. For this consumer the recovery invocation must include:

```text
echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow --config "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" --machine N --no-dry-run --recovery-mode --allow-device-reboot-recovery > /d/CodexRuntime/tiktok-video/recovery-final-mN-<timestamp>.log 2>&1; echo WORKER_EXIT=$?
```

If the operator requests parallelism above 12, launch 14 independent processes and record the actual count. Reserve enough monitoring calls to wait for all processes and perform final report/log collection; do not stop with a partial status merely because some workers have already exited.

## 4. Completion and failure handling

A target is successful only when its final report is `status=SUCCESS` with `post_verified=true`, or an explicitly equivalent automated accepted-and-verified result. `WORKER_EXIT=0` is only a transport/process result. Wait for all targets, then read each latest report and recovery log and map each target to a final outcome.

If a new failure signature appears, do not hot-edit production code during the live run. Record the exact signature, phase, attempts, report path, log path, and evidence path; keep the handoff lock and mark the target as needing a handler. Do not use manual ADB taps, back, reboot, or coordinate actions to force progress; all device changes must remain inside the workflow's registered handler/state machine.

## 5. Final response format

Report concisely in Vietnamese: released targets; backup and evidence paths; actual parallel count; per-target outcome; exact verified-success count; remaining signatures with exact report/log paths; and explicitly state that source was not modified, staged, committed, or pushed. Do not call a partial wait a complete recovery.
