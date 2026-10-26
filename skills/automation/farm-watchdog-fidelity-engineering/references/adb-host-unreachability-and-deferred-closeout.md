# Case Study: ADB Host Unreachability vs Zero-Device Fleet Discrimination & Deferred Daily Closeout

## Context & Incident Trigger
During late-night maintenance on the automation farm, remote ADB hosts (e.g. Farm Admin `192.168.110.119:5037`) periodically restart the ADB daemon via `restart_adb.py` to clear zombie transport tunnels. 

A 15-minute scheduled watchdog (`cron_clear_tiktok_cache.py`) ran during the 2-minute daemon restart window. 
Because `adb -H 192.168.110.119 -P 5037 devices` timed out after 15s and raised an exception, the function caught the error and returned `{}`.

## The Dual Failure Mechanism

### 1. Zero-Device False Equivalence
The reporting formatting calculated:
```python
c_fail_ids = [m for m in sorted(connected_fleet_machines) if min_m <= m <= max_m and m not in cleared_today]
# Since connected_fleet_machines for Admin was empty, len(c_fail_ids) == 0!
```
The resulting Telegram report printed:
```text
🏢 【FARM ADMIN - MÁY 201-280】
• Đã hoàn tất: 0 máy (None)
• Lỗi (0)
```
This falsely implied to the operator that 0 machines were processed with zero errors, triggering confusion and alarm that the Admin fleet had been cleared or broken.

### 2. Premature Daily Closeout Lockout
After printing the misleading report, the script executed:
```python
state_data["reported_date"] = today_str
save_state(state_data)
```
In subsequent 15-minute cron ticks (e.g. 04:00, 04:15, 04:30), the check `if state_data.get("reported_date") == today_str: return 0` caused the watchdog to immediately exit silently. Even though the remote ADB daemon had recovered at 03:47 and all 74 Admin machines were online and ready for cache cleaning, they were permanently skipped for the rest of the night.

## The Solution & Architectural Pattern

### 1. Explicit Cluster Reachability Tracking
Track reachability independently from connected device count:
```python
def get_connected_devices(cluster: dict) -> dict[str, str]:
    adb_cmd = [ADB, *cluster["adb_args"], "devices"]
    cluster["reachable"] = False
    for attempt in range(2):
        try:
            proc = subprocess.run(adb_cmd, capture_output=True, text=True, timeout=15, **WIN_KWARGS)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or f"adb exited with code {proc.returncode}")
            cluster["reachable"] = True
            ...
            return devices
        except Exception as exc:
            if attempt == 0:
                time.sleep(2)
                continue
            return {}
```

### 2. Transparent Cluster State in Reports
If a cluster is unreachable, emit an explicit anomaly notice and skip misleading 0-counts:
```python
if not cluster.get("reachable", True):
    report.append("⚠️ Cluster không kết nối được ADB; không thể xác nhận trạng thái máy.")
    continue
```

### 3. Deferred Daily Closeout
Only mark the session as concluded for the day if ALL clusters responded successfully, or under explicit `--force`:
```python
if all(cluster.get("reachable", True) for cluster in CLUSTERS) or args.force:
    state_data["reported_date"] = today_str
save_state(state_data)
```
When a cluster is unreachable, `reported_date` remains uncommitted, allowing future ticks within the active window (3h-5h) to automatically catch up as soon as the host daemon comes back online.
