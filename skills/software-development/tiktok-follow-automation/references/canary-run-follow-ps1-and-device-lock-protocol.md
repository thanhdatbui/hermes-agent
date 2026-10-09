# Canary `run-follow.ps1` Parameter Synchronization and Device Lock Protocol

## Context

When verifying follow runner fixes (`tiktok-follow`) via the convenience PowerShell script:
`powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1`

## 1. Parameter Synchronization in `run-follow.ps1`

`scripts/run-follow.ps1` defines defaults at the top:
```powershell
param(
    [int]$Machine = 13,
    [int]$AccountRowIndex = 2,
    [string]$Config = "config/machine6.yaml",
    [string]$Mode = "2",
    [switch]$ForcePreempt,
    [switch]$DryRun
)
```

### Pitfall
- Previous commits often update the default `$Machine` and `$AccountRowIndex` to the machine tested in that session.
- Note that `$Config` defaults to `"config/machine6.yaml"`. If running canary on a different machine (e.g. Machine 74), always pass `-Config "config/machine<N>.yaml"` explicitly, or verify that the machine configuration exists.
- When invoking directly with Python instead of PowerShell, ALWAYS use module syntax from repository root: `python -m follow_runner.run_follow ...`. Do NOT invoke `python follow_runner/run_follow.py` directly because `sys.path[0]` will be `follow_runner/`, triggering `ModuleNotFoundError: No module named 'follow_runner'`.
- If the operator/subagent asks to run bare `powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1`, verify whether the defaults in the script point to the target machine and row slot.
- If stale, synchronize the defaults in `run-follow.ps1` to match the target machine and row index, or pass `-Machine <N> -AccountRowIndex <slot> -Config config/machine<N>.yaml` explicitly on the command line.

## 2. Official Farm Owner & Fail-Closed BLOCKED Status

When a scheduled farm batch (e.g. `multi-machine-feed-session` on 80 devices) is currently executing:
- Check lock status: `python -c "import json, psutil; ..."` to inspect PID liveness.
- If the farm PID is active (`psutil.Process(pid).is_running() == True`), `run_follow.py` safely skips and returns:
  ```json
  {"status": "BLOCKED", "reason": "BLOCKED: [device-lock] máy <N> (<serial>) đang được User khóa bởi ...", "failed": true, "details": {"device_lock": ...}}
  ```
- **Operating Rule**: Never kill the official farm owner process or delete lock files to force a canary. Report status `BLOCKED` with the active PID and owner project details as verifiable evidence.

## 3. Canary Execution Timeout, Multi-Account Session Budget & Stale Lock Handling

### Session Duration Scaling
- A live follow run (`run_follow.py`) executes a full session budget by default (typically 12–15 follows across Mode 2 anchor traversal + Mode 1 search).
- On physical Android devices via ADB, each follow cycle takes 15–25 seconds (navigating to search/profile, waiting for UI render, dumping UI XML, tapping, pull-to-refresh reload verification, checking relationship state, returning to feed/list).
- Total duration for 12–15 follows is typically 3–6 minutes (180s–360s).
- **Pitfall**: Running terminal commands with short timeouts (e.g. `timeout 120s` or `180s`) can trigger a premature timeout signal while the runner is healthy and actively following accounts. Set `timeout >= 300s` (e.g. 360s) for live canary runs.

### Verifying Progress via State Files
- While or after running, check `runs/state/follow_state_<M>_row_<slot>.json`.
- Inspect UTC timestamps under `followed`, verify `budget_used`, `failed: {}`, `follow_failed: false`, and `fail_streak: 0`. Live timestamp progress confirms the runner is healthy and active.

### Premature Termination & Stale Lock Cleanup
- If the runner subprocess is terminated by terminal timeout or SIGTERM, the device lock file `~/.codex/device-locks/machine_<M>.lock.json` remains on disk with `status: "running"` and the old PID.
- Always verify PID liveness (`psutil.pid_exists(pid) == False`).
- Once confirmed dead, clean up the stale lock files (`machine_<M>.lock.json` and `serial_<serial>.lock.json`) so subsequent runs or cron batches are not falsely blocked.
