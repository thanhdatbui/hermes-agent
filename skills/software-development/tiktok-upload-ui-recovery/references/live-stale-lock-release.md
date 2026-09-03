# Live stale upload-lock release: reusable checklist

Use only for an explicitly authorized live rerun of the current TikTok upload launcher.

## Scope gate

Release a machine only when all conditions hold simultaneously:

- `project == "tiktok-upload"`
- `status == "handoff"`
- `owner_active == false`
- recorded PID is valid, belongs to the current host, and is proven dead with:
  `wmic process where "ProcessId=<pid>" get Name,ProcessId /format:list`
- no replacement `tiktok_workflow` worker exists for the target
- both aliases exist and match by content: `machine_<N>.lock.json` and `serial_<serial>.lock.json`
- project, status, owner state, PID, host, machine, serial, and `lock_id` agree across aliases

Keep foreign projects (`tiktok-luot nuoi acc`, `Tiktok_Reg`, gan-proxy), live/active locks, malformed or ambiguous aliases, and unverifiable PIDs. A dead PID alone is not enough for cross-project reclaim.

## Archive/evidence contract

Before unlinking either alias, create:

`C:\Users\Kibe\.codex\device-locks\backup_release_upload_<timestamp>\`

Copy both exact lock files into the backup. Write a sibling timestamped evidence JSON containing:

- `removed`: machine, serial, both aliases, PID, WMIC proof, backup paths
- `kept`: machine/identity, aliases, and every reason for retention
- replacement-worker scan result (record only redacted process identity; never persist secrets or full command lines)
- post-release remaining-lock verification and foreign-lock preservation result

Historical cleanup helpers are unsafe defaults: audit them before reuse. They may contain operator overrides, reclaim foreign feed locks, rely on `tasklist`, match filename prefixes only, or use `backup_takeover_*` names.

## Launcher and completion

Run the current full Tik1 launcher, not an old assignment manifest or worker ID, with `unset PYTHONPATH` when the launcher contract requires the pinned runtime. If preflight/version validation fails, record the blocker and do not edit source/config or bypass the check.

Run in a tracked background process with completion notification. Do not report success from parent exit code, timeout state, or launcher console lines alone. After completion, locate the corresponding newest `summary.csv`, correlate each target to its redacted report, and classify:

- `SUCCESS` only with `status=SUCCESS`, `verified=true`/equivalent report proof, and report evidence
- `SKIPPED_LOCKED` for preserved foreign locks
- new failures with their report/signature

Preserve `handoff` locks produced by new failures; post-run cleanup is not authorized by the original stale-lock release scope.
