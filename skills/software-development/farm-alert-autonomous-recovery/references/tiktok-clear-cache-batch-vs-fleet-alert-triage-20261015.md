# TikTok Clear Cache: Batch Retry vs Fleet Alert Discrepancy & Network ADB Timeout Triage

> Ref: `cron_clear_tiktok_cache.py`, `post_night_clear_cache_state.json`, `clear-tiktok-cache.py`.

## 1. Batch Retry Denominator Drift (Apparent Alert vs Report Contradiction)

### Symptom
- Farm Alert reports catastrophic failure: `Đa số máy dọn cache thất bại/timeout (31/36 máy fail)`.
- Follow-up Cronjob Report reports high overall success: `Đã hoàn tất: 123 máy, Lỗi (31): Kibe 7, Admin 24`.

### Root Cause Analysis
- **Execution Architecture**: Multi-tick cron running every 15 minutes across a time window (e.g. 03:00 - 05:00).
- State persistence (`post_night_clear_cache_state.json`) tracks `cleared_machines` cumulative set and `machine_retries` per-machine counter (max 2 retries).
- **The Denominator Trap**:
  - In initial ticks, the majority of the fleet (118+ devices) succeeds and enters `cleared_machines`.
  - In the final tick (e.g. 04:50), `target_machines` only contains the uncompleted remainder (36 machines).
  - Alert condition checks `f_count > total_attempted * 0.3` where `total_attempted = len(target_machines) == 36`.
  - With 31 persistent failures in that tick, alert fires formatted as `(31/36 máy fail)` (86% fail rate of the *batch*), even though fleet success is 123/154 (80% *fleet* success).
  - Immediately after the final tick, `has_retries_left` becomes `False` (all failed machines hit retry count 2), triggering the full daily summary report to stdout.

### Triage Procedure
1. Inspect `post_night_clear_cache_state.json`:
   - Compare `len(cleared_machines)` against `connected_fleet_machines`.
   - Inspect `machine_retries` distribution: distinguish between first-attempt flakes (retry=1 that succeeded) and terminal failures (retry=2).
2. Validate that failed machine list in the alert exactly matches the union of failed machines in cluster breakdown (e.g. Kibe 7 + Admin 24 = 31).
3. Do not treat localized batch denominator alerts as fleet-wide collapse before checking cumulative state.

---

## 2. Remote ADB Timeout Multiplier in UI Navigation Fallback

### Architecture
- Cluster `kibe`: Local USB / local ADB (`adb_socket: None`).
- Cluster `admin`: Network ADB (`tcp:192.168.110.119:5037`, `max_workers: 5`).

### Hierarchy of Attempts in `clear-tiktok-cache.py`
1. **Path 1**: Deep Link intent (`snssdk1180://clean_cache` / `snssdk1233://clean_cache`) -> O(1) direct landing on "Giải phóng dung lượng".
2. **Path 2**: In-App Settings Navigation -> Profile -> 3-bar Menu -> "Cài đặt và quyền riêng tư" -> swipe up to find "Giải phóng dung lượng" -> tap Xóa -> confirm modal.
3. **Path 3**: Home-screen widget probe.

### Failure Mechanism
- When Path 1 fails (unsupported deep link scheme on newer TikTok versions or cold app state), script falls back to Path 2.
- Path 2 executes 10–15 UI XML dumps (`dump_ui`) for navigation steps, menu detection, and swipe verification.
- On network ADB (Farm Admin), if `atx-agent` (TCP 7912) fails or is uninstalled, fallback to `uiautomator dump` takes 15–20s per invocation across the network bridge.
- `10 dumps * 15s + network ADB swipe latency > 240s` -> triggers `subprocess.TimeoutExpired` in wrapper runner.
