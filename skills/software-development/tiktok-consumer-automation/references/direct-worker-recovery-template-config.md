# Direct worker recovery: template config + exact lock takeover

Use this checklist only after the operator explicitly authorizes live recovery and names the machines.

## Preflight evidence

For every target:

- Read the newest target `report.json`; require `post_submission_state == None` before retrying. Record `status`, `reason`/failure signature, report path, and serial.
- Inspect exactly two lock aliases: `machine_<N>.lock.json` and `serial_<serial>.lock.json`.
- A stale handoff is eligible only when `status=handoff`, `owner_active=false`, and the recorded PID is absent from:
  `tasklist /FI "PID eq <PID>" /NH`.
- Windows `tasklist` prints `INFO: No tasks are running...` when absent. Do not classify any non-empty stdout as alive; check whether the numeric PID token appears in stdout.
- Check for a live competing `tiktok_workflow --machine N` process before archive/takeover.

## Archive contract

Create a timestamped directory under the shared lock root, copy the exact eight aliases for a four-machine example (or exactly two aliases per named target), write redacted `evidence.json`, then remove only those exact active aliases. Evidence should include timestamp, machine, serial, alias, recorded PID, PID-check result, source path, backup path, and prior report path. Never use a broad `*.lock.json` cleanup.

If a guard/parser fails, stop before moving aliases. Clean any empty failed archive directory and rerun the guard; do not continue based on an ambiguous PID result.

## Correct worker entrypoint

The worker binds the workbook row from `--machine`. Do not create or require per-machine config files. Use the existing template:

```text
config: D:\CodexRuntime\tiktok-video\config-machine-62.yaml
machine: N
log:    D:\CodexRuntime\tiktok-video\recovery-f4-mN-<timestamp>.log
```

Run each target in its own background process, not a shell loop:

```bash
cd /d/Taadaa/Tiktok-video && echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow --config "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" --machine N --no-dry-run > /d/CodexRuntime/tiktok-video/recovery-f4-mN-<timestamp>.log 2>&1; echo WORKER_EXIT=$?
```

Require the log line `effective config rebound to this row` as proof that template rebinding occurred.

## Completion proof

Do not use `WORKER_EXIT=0` as the success criterion. For every worker, wait for completion, resolve the `Report saved:` path from its log, and read the final report. Success requires:

```text
status=SUCCESS
post_verified=true
post_submission_state=ACCEPTED   # or the currently documented verified accepted state
```

After completion, inspect both final lock aliases. Verified-success workers should release them; blocked/manual targets retain them and must be reported. Keep excluded machines untouched and do not commit/push.
