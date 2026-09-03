# Gateway-reset cron recovery and launcher contract

Use this after a Hermes Gateway restart, Windows reset, or a report that the feed cron is `ok` but no machines moved.

## Evidence-first sequence

1. Treat cron `last_status=ok` / empty stdout as scheduler evidence only. It does **not** prove a child launcher or device session started.
2. Inspect the job output timestamp, `runner-live-lease/<day>.json`, the recorded PID tree, and the newest `runtime/<host>/live/<day>/` artifact directory.
3. A lease PID that is absent from `tasklist`/`psutil` is stale. Remove only that exact day lease; never remove a lease while any recorded child PID is alive.
4. Kick only `phase9-runner-tiktok-feed`, then verify: fresh lease start time, live PowerShell child, live `run_tiktok.py` child, and a new artifact with startup log. Do not restart Gateway or broad-kill processes as a first response.
5. If the child exits before device work, run the exact launcher command **without `-Run`**. This validates PowerShell parameter parsing, assignment preflight, and command construction without touching ADB/TikTok.

## Launcher/manifest contract checks

- `ACTIVE.json` is a pointer, not the assignment manifest. Resolve its `manifest_path` and pass the full `assignment-v1-*.json` to `-AssignmentManifest`; PowerShell assignment preflight expects the full manifest (`resources`, owner identity).
- Keep the argv contract symmetric across `tiktok_runner.py` -> `run-feed-session.ps1` -> `run_tiktok.py`. If the runner emits `-CohortArtifact`, the PS1 must declare `[string]$CohortArtifact` and forward `--cohort-artifact`; likewise forward `--assignment-manifest` and `--worker-id`.
- After a wrapper edit, run the no-`-Run` preflight and inspect its rendered command. Do not infer success from the parent process alone.

## Python environment contract

- A direct child launched by PowerShell can import `core.*` while a newer flow imports `python_runner.*`. `run_tiktok.py` must add the repository root (`Path(__file__).resolve().parents[1]`) to `sys.path` before flow imports.
- Remove inherited `PYTHONPATH` from the automation child environment. Otherwise Hermes' PIL can shadow the automation venv and produce a misleading `_imaging` import error. Verify the automation interpreter with `env -u PYTHONPATH ... run_tiktok.py --help` before retrying live.
- The runner's detached child must use the automation Python and preserve the resolved Windows paths; MSYS paths are for Git Bash only.

## Watcher notification rule

`HANDOFF`, `DEFERRED_LOCKED`, and `RECOVERY_IN_FLIGHT` are non-terminal/deferred states. Replaying historical `report.jsonl` must not print them as a fresh alert when the watcher uses `deliver: origin`; print only actionable alert states. Keep the underlying journal/reconcile state intact.

## Completion gate

A recovery is complete only when the new run has: (a) a fresh lease whose recorded PID is alive, (b) a live PowerShell + Python child command with the expected cohort/assignment/worker identity, and (c) a new artifact directory with startup evidence. Terminal machine summaries and cohort reconciliation are still required before claiming the batch succeeded.
