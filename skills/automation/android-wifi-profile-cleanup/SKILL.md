---
name: android-wifi-profile-cleanup
description: "Use when cleaning rogue Wi-Fi profiles on Android farms."
version: 1.0.0
author: Hermes Agent
tags: [android, wifi, farm, adb, cleanup, evidence]
---

# Android Wi-Fi Profile Cleanup

Use this class-level workflow when Android farm phones auto-connect to a non-farm SSID and must be returned to their fixed Aruba SSID. The goal is to remove only the confirmed rogue profile, preserve the farm profile, and leave a machine-level audit trail.

## Safety contract

- Never use a rogue SSID as a fallback or recovery network.
- **Saved Network Roam Trap**: Removing fallback logic from host Python scripts is NOT enough. If phones previously joined a rogue SSID, Android OS stores the profile in `WifiConfigStore.xml` (priority 100) and will auto-roam to it during radio toggles or AP load spikes. Cleanup MUST actively verify and re-bind all devices.
- Never remove a network by guessing an ID, by iterating through all IDs, or by trusting stale `dumpsys wifi` event history.
- Every device mutation runs under `D:/Taadaa/tools/with_device_lock.py --machine <N> -- ...` with the correct cluster/serial.
- Do not use `adb shell input tap`, `input keyevent`, or `input swipe` as a substitute for fixing network state.
- Do not read or expose Wi-Fi passwords in reports; use placeholders such as `<FARM_WIFI_PASSWORD>`.
- A device with no current rogue-SSID evidence is `NO_DAT_EVIDENCE` (or equivalent) and is not modified.

## Fixed target mapping

Resolve the machine number from the canonical workbook/mapping before changing anything:

- M01–M40 → `kibe 1`
- M41–M80 → `kibe 2`
- M201–M240 → `admin 1`
- M241–M280 → `admin 2`

Do not infer a target from the currently connected SSID. Do not move a phone between AP groups.

## Canary-first procedure

1. **Inspect one affected device.** Use the canonical O(1) inspection command where applicable, then obtain `dumpsys wifi` under the device lock.
2. **Require current-state proof.** Match the current `mWifiInfo` record for the rogue SSID and its current `Net ID`. A line in the historical `rec[...]` event list is not sufficient: the same ID may have been reused or the event may be stale.
3. **Remove exactly that ID.** On older Android builds where `cmd wifi` is unavailable, the validated low-level operation is:
   ```text
   adb shell service call wifi 14 i32 <CURRENT_ROGUE_NET_ID>
   ```
   Treat `Result: Parcel(... 00000001 ...)` as the service returning success, but still verify state afterward.
4. **Rejoin the fixed farm SSID & Shell Quoting Guard.** Clean-kill any existing loop (`am force-stop com.steinwurf.adbjoinwifi && pkill -f steinwurf`). Use `adb-join-wifi` with explicit quotes around SSIDs with spaces (e.g. `adb shell "am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid 'admin 1' -e password_type WPA -e password <PASS>"`).
   - **Root Cause of Re-Roam Trap**: Never send unquoted spaces. Without quotes, Android `/system/bin/sh` splits `admin 1` into `ssid="admin"` and extra arg `"1"`. The app logs `Trying to join: SSID: admin` (Net ID 3) and fails. Upon failure, Android OS automatically roams to the rogue SSID (e.g. `Dat`) due to high priority and strong signal (-40dBm).
   - Quoting with `'admin 1'` ensures `adbjoinwifi` receives the full SSID, connects to Net ID 1, and reaches `Device Connected to admin 1` (RSSI -56dBm).
5. **Read back immediately.** Confirm `Supplicant state: COMPLETED`, the current SSID is the mapped farm SSID, and the address is in `192.168.110.x`. Read configured networks through Wi-Fi service output and confirm the rogue profile is absent where the platform exposes it.
6. **Only after canary verification, batch.** Run a background launcher with completion notification, one locked operation per machine, bounded concurrency (`max_workers=20` for 80–160 machines to finish in ~1–2 minutes, avoiding slow 30–60 min serial runs), and a separate JSON result per machine. Do not poll the background process with `ps`, `pgrep`, or sleep loops; wait for the completion event, then inspect the result artifacts.

## Batch result contract

Each machine result should include:

- machine number, cluster, serial
- `rogue_active_id` or an explicit no-evidence status
- removal transaction result (verified against `Parcel(... 00000001 ...)`; never increment `deleted_networks` if binder returned `SecurityException` or failed — record as `PERMISSION_DENIED` under `failed_deletes`)
- mapped target SSID
- post-action current Wi-Fi summary
- `ip_ok` for `192.168.110.x`
- whether the rogue profile is still present in the configured-network readback
- lock/wrapper errors separately from device-operation errors

Use status values such as `NO_DAT_EVIDENCE`, `CLEAN_AND_ONLINE`, `ONLINE_BUT_ROGUE_SAVED`, `CLEAN_BUT_VERIFY`, and `ERROR`. Do not report the batch as complete until the artifacts have been read and summarized.

## Kỷ luật báo cáo chống làm tròn & chống giấu máy kẹt lock
- **BẮT BUỘC liệt kê máy kẹt lock (LOCK_TIMEOUT):** Khi chạy batch farm, TUYỆT ĐỐI CẤM gộp số liệu hoặc chỉ báo cáo phần trăm máy thành công mà lờ đi các máy bị skip do lock bận ca. Mọi máy dính `LOCK_TIMEOUT` BẮT BUỘC phải xuất rõ danh sách số máy cụ thể (VD: `M1..M80 kẹt lock`).
- **CẤM báo DONE khi chưa đọc ngược cấu hình (Read-back verification):** Không bao giờ suy diễn "đã xóa thành công" chỉ vì script đã bắn lệnh `service call wifi 14`. Trên các dòng máy Samsung Hàn Quốc (SM-G930S/L/K), lệnh shell UID 2000 bị chặn `SecurityException`. BẮT BUỘC phải đọc lại `dumpsys wifi` hoặc kiểm tra `WifiConfigStore.xml` để xác nhận profile rác đã thực sự biến mất khỏi danh sách đã lưu.


## Failure handling

- If the current-state Net ID cannot be identified unambiguously, stop mutation for that device and mark it blocked with the raw evidence.
- If removal succeeds but the mapped farm SSID does not complete with a farm-subnet IP, preserve the evidence and mark `CLEAN_BUT_VERIFY`; do not try another SSID.
- If a device lock cannot be acquired, leave the device untouched and report the lock owner/timeout.
- If a batch is interrupted, distinguish completed per-device artifacts from unprocessed machines; never infer success from the launcher exit code alone.
- **Static IP Configuration Trap**: If a device's saved profile has `IP assignment: STATIC`, toggling Wi-Fi retains the stale static IP (e.g. `192.168.10.x`). The profile MUST be deleted via `service call wifi 14 i32 <ID>` and re-joined via `adbjoinwifi` so Android re-initiates DHCP lease negotiation on `192.168.110.x`.
- **Foreground ADBJoinWifi Freeze & Radio Toggle Loop Trap**: Khi thiết bị kẹt ở màn hình ADBJoinWifi (`mCurrentFocus=Window{... com.steinwurf.adbjoinwifi/com.steinwurf.adbjoinwifi.MainActivity}` hiển thị "Trying to connect to:"), các watchdog nền bật/tắt Wi-Fi (`setWifiEnabled(false/true)`) không thể tự giải phóng giao diện này. BẮT BUỘC thực thi: (1) `am force-stop com.steinwurf.adbjoinwifi`, (2) Rà soát xóa profile lỗi/static và re-join bằng `am start ... --es ssid "<SSID>" ...`, (3) Đợi 4 giây và BẮT BUỘC gửi `input keyevent 3` để đóng Activity về Home/Launcher, (4) Xác minh focus qua `inspect_machine.py` và chụp screencap nghiệm thu.
- **Korean Firmware Binder Permission Trap (G930S/L/K vs G930F)**: On Korean variants (`herolteskt-user`, security patch late-2020), `service call wifi 14` from shell UID 2000 is rejected with `SecurityException: Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE`. On these devices, do NOT attempt `pm grant` (it fails); instead rely on `adbjoinwifi` to force-bind the target Aruba SSID as active with DHCP, preventing auto-roam. Carrier profiles (`ollehWiFi`, `KT WiFi`, `T wifi zone_secure`, `U+zone`) cannot be deleted via shell, but are harmless in Vietnam since no matching carrier SSIDs broadcast. The true threats to eliminate are local broadcasts (`Dat`, `Dat-1`, `BOX`, un-numbered `kibe`/`admin`).
- **`dumpsys wifi` Event History Regex Trap (`rec[...]` vs Configured Networks)**: A naive regex like `re.finditer(r"ID:\s*(\d+)\s+SSID:\s*...", out)` against the full ~14,000-line `dumpsys wifi` dump matches historical `rec[...]` state transitions from hours/days prior, falsely alerting on networks that were already deleted. Parsers must restrict matching to the active `Configured networks:` block or evaluate the current `mWifiInfo` / `wpa_supplicant` state.
- **Lock-Timeout Deferred Sweep Trap**: Farm batch runners (`batch_clean_farm_wifi.py`) enforce `operator_device_lock` with timeout (e.g. 45s). Devices running active TikTok/feed sessions will time out (`LOCK_TIMEOUT`) and be skipped to protect production jobs. A single batch run will NOT achieve 100% cleanup if devices are in active rotation; always check lock count (`~/.codex/device-locks/`) and run a secondary sweep once locks drop to 0.
- **Preflight Prerequisite Integration**: Feed runners (`run-feed-session.ps1`, `tiktok_runner.py`) MUST export `FARM_WIFI_PROFILES_FILE=D:\Taadaa\machine-config\farm_wifi_profiles.json` so runner Stage 2 auto-recovery does not fail closed due to missing credentials. Telemetry emits `WIFI_PROFILES_FILE_LOAD path=farm_wifi_profiles.json` on load.

## Production Automation Scripts
- `D:/Taadaa/tools/scan_rogue_wifi_farm.py`: Fast non-intrusive pre-scan script across both clusters (Dual-Cluster Farm) to audit rogue Wi-Fi networks, active SSIDs, and IP assignment across all attached devices in ~10s without modifying state or blocking on write locks.
- `D:/Taadaa/tools/batch_clean_farm_wifi.py`: Parallel locked cleanup across Dual-Cluster Farm (M1-80 & M201-280, max_workers=20), removing rogue networks (`Dat`, `Dat-1`, `BOX`, `Green Media 5G`, `admin`, `kibe`) and enforcing pure Aruba SSID binding with DHCP.
- **ADB Binary Path Invariant**: Always prefer `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`. Avoid paths containing parentheses such as `C:\Program Files (x86)\...` which trigger Hermetic Shell Guard false-positives on subshell parenthesis syntax `(...)`.
- **Subagent Delegation Contract**: When delegating Wi-Fi rescue or device cleanup to subagents, avoid `TASK_KIND: INVESTIGATE` if device mutation or script execution is expected (as `INVESTIGATE` enforces strict `[READ-ONLY WORKER]` guards). Launch `batch_clean_farm_wifi.py` directly via `terminal(background=True, notify_on_complete=True)` from Coordinator.

## Reference

- See `references/korean-firmware-binder-permission-and-static-ip-trap.md` for firmware variant differences (G930F vs G930S), SecurityException mechanics, and Static IP remediation.
- See `references/validated-rogue-ssid-canary.md` for the Android 8 binder transaction and read-back evidence pattern from the validated canary. This reference deliberately omits credentials and machine-specific secrets.
- See `references/runner-preflight-wifi-fallback-and-roam-triage.md` for the feed runner preflight credentials fallback failure (`FARM_WIFI_PROFILES_FILE`) and rogue SSID roam proxy outage root causes.
- See `references/operational-closeout-gate-rubric.md` for the mandatory 4-pillar artifact requirements (raw logcat proof, 100% farm device accounting, automated pytest suite, timeline isolation) to pass `closeout_gate.py --input` with Sol Auditor (>= 85 pts APPROVED).
