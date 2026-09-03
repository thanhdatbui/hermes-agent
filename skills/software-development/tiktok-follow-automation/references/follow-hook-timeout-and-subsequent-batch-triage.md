# Follow Hook Timeout and Subsequent Batch Triage

## Context
When `multi_machine_feed_session.py` invokes `follow_runner/run_follow.py` as a subprocess hook, it enforces a timeout budget (default `DEFAULT_FOLLOW_HOOK_TIMEOUT_SECONDS = 900.0` or `follow_timeout_seconds`).
If `run_follow.py` exceeds this budget (e.g. due to slow feed startup, recovery ladder loops, or network latency during `open_tiktok`), `multi_machine_feed_session` catches `subprocess.TimeoutExpired`, terminates the python subprocess, executes `_force_stop_tiktok_and_home`, records `status: "timeout"`, `reason: "follow-timeout"` in `follow_result.json`, and emits a Farm Alert `🚨 [MÁY N] DỪNG PHIÊN • Script: tiktok-follow • Lý do: follow-timeout`.

## Triage Recipe

1. **Locate Incident vs Subsequent Batch Artifacts**:
   - Inspect live run directories under `D:\Taadaa\runtime\<host>\live\<date>\` for the incident batch and any subsequent batches run on the same date.
   - Read `follow_result.json` in `D:\Taadaa\runtime\<host>\live\<date>\<batch>\machines\machine_<N>\<run_id>\follow_result.json` across batches.
   - Check if subsequent batches completed with `status: "OK"` and non-zero `followed_count`.

2. **Inspect Machine Follow State**:
   - Read `D:\Taadaa\tiktok-follow\runs\state\follow_state_<N>_row_<slot>.json`.
   - Check `budget_used`, `followed` timestamps, and verify `follow_failed: false`.
   - If subsequent batches succeeded and `follow_failed` is false, the timeout was an isolated transient incident at that specific batch tick.

3. **Check Device Liveness & Lock State**:
   - Verify device connectivity via `adb devices`.
   - Ensure `runtime/<host>/device_locks` has no stale or orphaned locks for machine N.
   - Check device UI state via dump/screencap to ensure launcher/home is clean and responsive.
