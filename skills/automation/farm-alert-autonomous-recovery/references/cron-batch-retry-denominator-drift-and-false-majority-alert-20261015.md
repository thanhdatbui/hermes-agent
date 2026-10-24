# Cron Batch Retry Denominator Drift & False Majority Alert Triage

> Protocol reference for multi-stage batch cron jobs across Taadaa Phone Farm (Kibe 1-80 & Admin 201-280).

## 1. Symptom: Contradictory Alert vs Cronjob Response

In multi-stage / rolling cron jobs that perform fleet-wide operations in recurring ticks (e.g., `cron_clear_tiktok_cache.py`, night 2FA, avatar uploader):
- **Alert message:** `🚨 [FARM ALERT: LỖI SCRIPT / PIPELINE] Đa số máy dọn cache thất bại/timeout (31/36 máy fail): ...`
- **Followed immediately by Cronjob Response:** `[BÁO CÁO DỌN DẸP CACHE TIKTOK] • Đã hoàn tất: 123 máy (Kibe: 71, Admin: 52) • Lỗi (31): ...`
- **User reaction:** Confusion over why an alert claims "Đa số thất bại" (86% fail) when 123/154 machines (80%) succeeded.

## 2. Root Cause: Batch Denominator vs Fleet Denominator

1. **Denominator Drift:**
   - In stage 1 (initial run), 118 machines succeed on their first attempt.
   - In stage 2 (retry tick), only un-cleared machines are scheduled: `total_attempted = len(target_machines) = 36`.
   - Out of the 36 retried machines, 5 succeed and 31 fail again.
   - Flawed alert logic evaluates `f_count > total_attempted * 0.3` where `total_attempted` is ONLY the retry batch (36), not the fleet (154).
   - As a result, `31/36` (86%) trips the threshold and emits a false-majority alarm ("Đa số máy thất bại").

2. **Premature Alert During In-Flight Retries:**
   - Alert evaluation fired before retries were exhausted, panicking users while subsequent cron ticks were still actively reconciling the remaining machines.

## 3. Canonical Fix Pattern (Fleet-Gated Alerting)

Multi-stage cron jobs MUST evaluate failure alerts against the **entire connected fleet** and ONLY after retries have been exhausted:

```python
all_done = bool(connected_fleet_machines and connected_fleet_machines.issubset(cleared_today))
has_retries_left = any(
    m not in cleared_today and machine_retries.get(str(m), 0) < MAX_RETRIES
    for m in connected_fleet_machines
)
total_fleet = len(connected_fleet_machines)
total_unresolved = len([m for m in connected_fleet_machines if m not in cleared_today])

# Only alert if retries are fully exhausted AND failure rate exceeds fleet threshold
if not has_retries_left and total_fleet > 0 and total_unresolved >= 10 and total_unresolved > (total_fleet * 0.3):
    f_summary_str = ", ".join(f"{m:02d} ({r})" for m, r in sorted(failed_machines))
    alert_msg = f"Tỷ lệ dọn cache thất bại cao ({total_unresolved}/{total_fleet} máy chưa xong sau retry): {f_summary_str}"
    if state_data.get("last_alert_date") != today_str or state_data.get("last_alert_msg") != alert_msg:
        _send_clear_cache_alert(alert_msg)
        state_data["last_alert_date"] = today_str
        state_data["last_alert_msg"] = alert_msg
        save_state(state_data)
```

### Key Invariants:
1. **Never use batch size (`len(target_machines)`) as denominator** in alert messages for multi-stage jobs.
2. **Never claim "Đa số thất bại"** when the fleet success rate is >= 70-80%.
3. When fleet success is acceptable (e.g., 80%), let the standard cron report stdout deliver the failure breakdown without firing emergency Farm Alerts.

## 4. Triage of Device Timeouts (ADB Daemon / Transport Hang)

When machines report `Timeout` during batch operations:
1. Run quick inspection: `python D:/Taadaa/tools/inspect_machine.py <N>`.
2. If `run_cmd` times out on `getprop ro.product.model` after 10s:
   - Device has an ADB daemon freeze or USB hardware drop.
   - Child execution scripts with high timeouts (e.g., 240s) will block worker slots for 4 minutes per hung device.
3. Pre-flight probe pattern:
   - Before launching long sub-processes on a device, run a 3-5s quick ADB ping (`adb shell echo 1`).
   - If unresponsive, fail fast immediately to avoid starving worker pool threads (especially on remote Admin farm with 5 max workers).
