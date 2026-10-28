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
- **CẤM BÁO "ĐỂ IM CHỜ TỰ PHỤC HỒI" KHI CHƯA ĐỐI SOÁT CỜ PHẠT / XÁC THỰC:** Tuyệt đối CẤM suy đoán thụ động "chờ qua đêm/chờ sáng mai Wi-Fi tự phục hồi". Khi máy mất IP hoặc không kết nối, bắt buộc trích xuất ngay cờ `mNetworkSelectionDisableReason` trong `dumpsys wifi` và chạy WinRT OCR trên màn hình Cài đặt Wi-Fi. Nếu thấy dòng đỏ **"Đã xảy ra lỗi xác thực"** (`DISABLED_BY_WRONG_PASSWORD` / `ASSOCIATION_REJECTION`), Android OS sẽ **bỏ qua vĩnh viễn SSID đó trong mọi chu kỳ quét nền** — tình trạng này KHÔNG BAO GIỜ tự khỏi nếu không can thiệp xóa profile kẹt và nạp lại mật khẩu chuẩn.
- **Poison SSID Strict Blacklist (`Dat`, `Dat-1`, `BOX`)**: Tuyệt đối CẤM đưa các SSID ngoại lai ngoài farm (`Dat`, `Dat-1`, `BOX`) vào bất kỳ file cấu hình, tài liệu, script cứu hộ, hoặc logic fallback nào. Mọi SSID ngoài 4 AP Aruba quy hoạch cứng (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`) đều là Poison SSID — hành động duy nhất được phép khi phát hiện là tiêu diệt/xóa vĩnh viễn (Purge/Forget) khỏi toàn bộ thiết bị. CẤM TUYỆT ĐỐI agent/script tự ý thử kết nối vào `Dat` để "chữa cháy" hay "test".
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
- **CẤM khẳng định 100% sạch (Fake Clean Claims) khi mới chỉ test Canary 1 máy:** Tuyệt đối không bao giờ suy diễn từ kết quả thử nghiệm trên 1 máy (ví dụ M221) thành "toàn bộ cụm đã xóa xong". Phải đối soát qua báo cáo tổng hợp `batch_wifi_cleanup_result.json`, kiểm tra trường `failed_deletes` (PERMISSION_DENIED) và quét ngược lại `dumpsys wifi` trên toàn bộ các máy mục tiêu trước khi chốt hạ.
- **Phân biệt sóng đang phát (Broadcasting) vs Profile lưu ngầm không phát sóng (`Dat` vs `Dat-1`):** Trong giao diện Wi-Fi Settings của Samsung S7 Hàn (SM-G930S), chỉ những SSID đang thực sự phát sóng trong môi trường RF (như `Dat`) mới xuất hiện trong danh sách "MẠNG ĐANG CÓ" để thực hiện Long-press xóa qua UI. Các SSID lưu ngầm nhưng không phát sóng (như `Dat-1`) bị Knox ẩn khỏi `WIFI_SAVED_NETWORK_SETTINGS`. Để triệt tiêu sóng đang đe dọa, luôn dùng kỹ thuật Long-press tại hàng 1 `(304, 820)` -> `(500, 1195)` "Quên mạng" hoặc tap mạng đang active tại `(300, 530)` -> `(876, 1412)` "QUÊN".
- **CẤM báo DONE khi chưa đọc ngược cấu hình (Read-back verification):** Không bao giờ suy diễn "đã xóa thành công" chỉ vì script đã bắn lệnh `service call wifi 14`. Trên các dòng máy Samsung Hàn Quốc (SM-G930S/L/K), lệnh shell UID 2000 bị chặn `SecurityException`. BẮT BUỘC phải đọc lại `dumpsys wifi` hoặc kiểm tra `WifiConfigStore.xml` để xác nhận profile rác đã thực sự biến mất khỏi danh sách đã lưu.
- **Giành Lock khi Operator chỉ đạo (OPERATOR_PREEMPT):** Khi User/Operator phát lệnh giành lock (VD: *"Giành lock đi. Ca nuôi nick hết luôn r thì phải"*), sử dụng `force_preempt=True` trong `operator_device_lock` hoặc cờ `--preempt` trên tool `batch_clean_farm_wifi.py`. Cơ chế này kích hoạt `takeover_scope="OPERATOR_PREEMPT"` của `automation-core`, giành quyền can thiệp an toàn ngay lập tức mà không cần xóa tay file `.lock.json` bừa bãi.
- **Tránh bẫy ảnh đen khi nghiệm thu (Visual Sleep Trap):** Khi chụp ảnh màn hình nghiệm thu (`screencap`) gửi User kèm thẻ `MEDIA:<path>`, BẮT BUỘC kiểm tra trạng thái màn hình (`dumpsys power` hoặc qua `inspect_machine.py`). Nếu máy đang ở trạng thái `OFF (Sleep/Dozing)`, ảnh chụp sẽ là màn hình đen xì. Phải đảm bảo máy sáng màn hình trước khi chụp và BẮT BUỘC chạy WinRT OCR kiểm chứng tận mắt nội dung hiển thị (icon, SSID, giờ hệ thống) trước khi gửi. Tuyệt đối cấm gửi ảnh mù hoặc gửi đối phó.


## Failure handling

- If the current-state Net ID cannot be identified unambiguously, stop mutation for that device and mark it blocked with the raw evidence.
- If removal succeeds but the mapped farm SSID does not complete with a farm-subnet IP, preserve the evidence and mark `CLEAN_BUT_VERIFY`; do not try another SSID.
- If a device lock cannot be acquired, leave the device untouched and report the lock owner/timeout.
- If a batch is interrupted, distinguish completed per-device artifacts from unprocessed machines; never infer success from the launcher exit code alone.
- **Static IP Configuration Trap**: If a device's saved profile has `IP assignment: STATIC`, toggling Wi-Fi retains the stale static IP (e.g. `192.168.10.x`). The profile MUST be deleted via `service call wifi 14 i32 <ID>` and re-joined via `adbjoinwifi` so Android re-initiates DHCP lease negotiation on `192.168.110.x`.
- **Stale Dialog Settings Trap & Clean State Invariant (`am force-stop com.android.settings`)**: Khi tự động hóa UI Cài đặt Wi-Fi (`android.settings.WIFI_SETTINGS`), nếu phiên trước đó để lại modal/dialog treo (ví dụ popup hỏi mật khẩu của mạng lạ hay dialog cấu hình), mở lại Settings sẽ bị dialog cũ nằm đè lên che khuất danh sách mạng. Các cú tap mù theo tọa độ sẽ rơi trúng checkbox hoặc nút "KẾT NỐI" của dialog cũ thay vì mạng mục tiêu. BẮT BUỘC: Luôn gọi `am force-stop com.android.settings` trước khi gọi `am start -a android.settings.WIFI_SETTINGS` để đảm bảo giao diện Settings mở lên ở trạng thái sạch hoàn toàn (clean state).
- **Foreground ADBJoinWifi Freeze & Radio Toggle Loop Trap**: Khi thiết bị kẹt ở màn hình ADBJoinWifi (`mCurrentFocus=Window{... com.steinwurf.adbjoinwifi/com.steinwurf.adbjoinwifi.MainActivity}` hiển thị "Trying to connect to:"), các watchdog nền bật/tắt Wi-Fi (`setWifiEnabled(false/true)`) không thể tự giải phóng giao diện này. BẮT BUỘC thực thi: (1) `am force-stop com.steinwurf.adbjoinwifi`, (2) Rà soát xóa profile lỗi/static và re-join bằng `am start ... --es ssid "<SSID>" ...`, (3) Đợi 4 giây và BẮT BUỘC gửi `input keyevent 3` để đóng Activity về Home/Launcher, (4) Xác minh focus qua `inspect_machine.py` và chụp screencap nghiệm thu.
- **Korean Firmware Binder Permission Trap & UI Settings Forget Pattern (G930S/L/K vs G930F)**: On Korean variants (`herolteskt-user`, security patch late-2020), `service call wifi 14` from shell UID 2000 is rejected with `SecurityException: Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE`. On these devices, `WIFI_SAVED_NETWORK_SETTINGS` hides saved networks, but `android.settings.WIFI_SETTINGS` allows UI removal:
  - **Bẫy 1-chạm (Single-tap trap) vs Kỹ thuật Long-press (Chuẩn hóa 100%)**: Khi SSID đang ngắt kết nối trong danh sách "MẠNG ĐANG CÓ", tap 1 chạm sẽ kích hoạt lệnh kết nối và xoay vòng DHCP, không hiện nút Quên. Thao tác chuẩn xác 100% là:
    1. `am force-stop com.android.settings` (bắt buộc dọn sạch popup cũ).
    2. `am start -a android.settings.WIFI_SETTINGS` và chờ 3s.
    3. **Long-press 1.2s** tại hàng 1 `(304, 820)`: `input swipe 304 820 304 820 1200`.
    4. Menu ngữ cảnh Android bật lên -> Tap vào mục **"Quên mạng"** tại tâm **`(500, 1195)`** (bounds `[374, 1171, 614, 1217]`). Profile lập tức bị xóa sổ vĩnh viễn.
  - **Kịch bản phụ (Khi mạng rác đang là MẠNG HIỆN TẠI)**: Tap vào SSID đang kết nối tại `(300, 530)` mở modal chi tiết mạng -> Tap nút **"QUÊN"** ở góc dưới phải tại tâm **`(876, 1412)`** (bounds `[828, 1389, 925, 1436]`).
  - Ngay sau khi xóa, re-bind về đúng AP quy hoạch bằng `adbjoinwifi` bọc nháy kép chuẩn (`--es ssid "admin 1"`).
  - Carrier profiles (`ollehWiFi`, `KT WiFi`, `T wifi zone_secure`, `U+zone`) cannot be deleted via shell, but are harmless in Vietnam since no matching carrier SSIDs broadcast. The true threats to eliminate are local broadcasts (`Dat`, `Dat-1`, `BOX`, un-numbered `kibe`/`admin`).
- **Parallel Execution Invariant (Cấm cuốn chiếu)**: Khi chạy xóa hoặc cấu hình Wi-Fi hàng loạt trên farm, BẮT BUỘC chạy song song đa luồng (`ThreadPoolExecutor` max_workers = số máy mục tiêu, 15-20 workers) để xử lý đồng loạt. TUYỆT ĐỐI CẤM chạy tuần tự cuốn chiếu (rolling/serial); việc ngắt kết nối từng máy một sẽ khiến các máy xung quanh nhảy roam sang sóng rác của nhau, gây bão kết nối (re-roam storm) và kéo dài thời gian xử lý.
- **Fake Cleanup Metric Trap (Audit Parcel Response)**: Never assume `service call wifi 14` succeeded just because the command returned exit code 0. Always parse stdout/stderr: only `Parcel(... 00000001 ...)` means deleted. If `SecurityException` appears, increment `failed_deletes` (PERMISSION_DENIED) and classify machine status as `ONLINE_BUT_ROGUE_SAVED`. Never report 100% clean when profile deletion was rejected by Knox/ROM.
- **Reporting Discipline & No Lock-Hiding Trap**: When reporting farm batch results, NEVER hide or omit machines skipped due to `LOCK_TIMEOUT` to inflate completion rates. Skipped machines due to active farm runs MUST be explicitly enumerated (e.g. `Kẹt lock bận ca: 36 máy`), and follow-up sweeps MUST only run when machines are confirmed idle.
- **`dumpsys wifi` Event History Regex Trap (`rec[...]` vs Configured Networks)**: A naive regex like `re.finditer(r"ID:\s*(\d+)\s+SSID:\s*...", out)` against the full ~14,000-line `dumpsys wifi` dump matches historical `rec[...]` state transitions from hours/days prior, falsely alerting on networks that were already deleted. Parsers must restrict matching to the active `Configured networks:` block or evaluate the current `mWifiInfo` / `wpa_supplicant` state.
- **Lock-Timeout Deferred Sweep Trap**: Farm batch runners (`batch_clean_farm_wifi.py`) enforce `operator_device_lock` with timeout (e.g. 45s). Devices running active TikTok/feed sessions will time out (`LOCK_TIMEOUT`) and be skipped to protect production jobs. A single batch run will NOT achieve 100% cleanup if devices are in active rotation; always check lock count (`~/.codex/device-locks/`) and run a secondary sweep once locks drop to 0.
- **Preflight Prerequisite Integration**: Feed runners (`run-feed-session.ps1`, `tiktok_runner.py`) MUST export `FARM_WIFI_PROFILES_FILE=D:\Taadaa\machine-config\farm_wifi_profiles.json` so runner Stage 2 auto-recovery does not fail closed due to missing credentials. Telemetry emits `WIFI_PROFILES_FILE_LOAD path=farm_wifi_profiles.json` on load.
- **Dual-Cluster Mapping Fallback Trap (`vpn_preflight.py`)**: Trong mô hình farm 2 cụm (Kibe M1–M80 vs Admin M201–M280), hàm `get_wifi_credentials_for_serial` phân giải serial qua workbook `PROXYgandienthoai.xlsx` của host mặc định. Khi máy Admin chạy trên điều phối Kibe, tra cứu serial sẽ ra `None`, khiến Stage 2 auto-join Wi-Fi (`adbjoinwifi`) bị bỏ qua hoàn toàn. BẮT BUỘC hàm này phải có cơ chế fallback sang file mapping của cụm đối ứng (`kibe` <-> `admin`) để luôn lấy được đúng target SSID (`admin 1`, `admin 2`, `kibe 1`, `kibe 2`).
- **Auto-Healer Subnet Regex Trap (`192.168.110.x` vs `192.168.x.x`)**: Auto-healers and watchdogs (e.g. `farm_wifi_auto_healer.py`) MUST strictly regex-match the farm subnet `192.168.110.\d+`. A loose pattern `192.168\.\d+\.\d+` incorrectly treats rogue IPs (such as `192.168.10.x` from `Dat-1`) as healthy, causing the auto-healer to skip recovery, leaving devices to fail immediately under feed runner proxy kill-switches.
- **DHCP Lease Timing Window on Samsung S7 (Timing Window >= 6s)**: On Samsung S7 Android 8 devices connecting to Aruba APs, WPA2 handshake plus DHCP lease negotiation requires 5–7 seconds. Runner preflight and recovery handlers calling `adbjoinwifi` MUST allow at least 6–8s of settle time before probing `dumpsys connectivity` or `ip addr`. Probing at <= 4s produces false-positive `dumpsys connectivity: Wi-Fi not connected` preflight blockages.
- **SystemUI `wifi_combo` False-Positive Trap & Switcher Offline Abortion**:
  - Khi runner kiểm tra cờ offline trong UI (`_switcher_offline_reason(popup_xml)` tìm chuỗi `"khong co internet"`), việc quét toàn bộ `popup_xml` sẽ vô tình bắt trúng thuộc tính `content-desc="Tín hiệu Wi-Fi đủ.,Không có Internet."` của icon Wi-Fi trên thanh trạng thái đỉnh máy (`com.android.systemui:id/wifi_combo`).
  - Triệu chứng: Máy chạy HTTP Proxy (`192.168.110.2:100xx`), Android captive portal (`generate_204`) bị trễ khiến SystemUI hiện icon chấm than hoặc "Không có Internet". TikTok thực tế vẫn có mạng, danh sách switcher đã hiện đầy đủ nick đích, nhưng runner hủy chuyển nick với lý do `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)`.
  - Hậu quả: Watchdog phân loại chuỗi `wifi_combo` thành **"Mất kết nối Wi-Fi (AP)"**, tạo ra **ảo giác AP rớt sóng**.
  - Khắc phục: Bắt buộc chỉ kiểm tra chuỗi offline bên trong package TikTok (`com.ss.android.ugc.trill`) và loại trừ toàn bộ cây node thuộc `com.android.systemui`.
- **ADBJoinWifi Shell Quoting & Activity Lifecycle**: Commands invoking `adbjoinwifi` MUST pass `--es ssid "<SSID>"` with explicit quotes. Unquoted `-e ssid kibe 1` splits the SSID into `ssid="kibe"` and arg `"1"`. Always prepend `am force-stop com.steinwurf.adbjoinwifi` and follow with `input keyevent 3` to return to Home/Launcher.
- **Aruba Association Rejection & Flapping Unwanted Network Trap (`CMD_UNWANTED_NETWORK` & False AUTHENTICATION_FAILURE)**:
  - Khi máy có RSSI suy hao (<= -72 dBm trên băng tần 5GHz) hoặc AP Aruba đạt ngưỡng tải/Client Match, AP nhả cờ `ASSOCIATION_REJECTION` (level 2 failure). Khi bắt tay 4 bước (4-Way Handshake) bị drop, Android kích hoạt cờ heuristic sai lệch `updateNetworkSelectionStatusForWrongPassword` (`AUTHENTICATION_FAILURE`), tạm thời đưa SSID chuẩn vào blacklist không tự kết nối.
  - Cảnh báo Auto-Healer Flapping: Nếu cronjob/watchdog liên tục gọi `forcinglyEnableAllNetworks` rồi re-join qua `adbjoinwifi` (UID 10179), hệ thống Samsung Knox chặn quyền ghi cấu hình (`UID 10179 does not have permission to update configuration`), làm NetworkMonitor hạ điểm mạng xuống ~52 và phát `CMD_UNWANTED_NETWORK`, ngắt kết nối đẩy `wlan0` về lại `state DORMANT / NO-CARRIER`.
  - Profile rác trùng tiền tố (`kibe` vs `kibe 1`): Cấu hình rác open không bảo mật mang tên gốc `kibe` (Net ID 1) sẽ tranh chấp quét mạng với `kibe 1` (Net ID 0), khiến máy dao động liên tục giữa `last="kibe"NONE` và `target="kibe 1"WPA_PSK`. Bắt buộc phải purge dứt điểm bằng `service call wifi 14 i32 <ROGUE_ID>`.
  - Biện pháp khắc phục: (1) Purge triệt để profile rác trùng tiền tố, (2) `am force-stop com.steinwurf.adbjoinwifi`, (3) Toggle radio `svc wifi disable && sleep 1 && svc wifi enable`, (4) Kiểm tra vị trí đặt máy vật lý / ăng-ten để đảm bảo RSSI 5GHz > -70 dBm, hoặc khởi động lại AP Aruba tương ứng nếu AP vẫn lưu cờ blacklist MAC.

- **Bẫy Sai Mật Khẩu Wi-Fi Theo Nhóm Máy & Triệu Chứng Aruba MIC Failure (2026-10-18)**:
  - CẤM TUYỆT ĐỐI agent phản xạ dùng mật khẩu `19051995` cho toàn bộ các AP trên farm. Nguồn chân lý duy nhất (Single Source of Truth) là `D:/Taadaa/machine-config/farm_wifi_profiles.json`:
    * M1–M40 (`kibe 1`): Mật khẩu bắt buộc là **`23102025`**.
    * M41–M80 (`kibe 2`): Mật khẩu là **`19051995`**.
    * M201–M240 (`admin 1`): Mật khẩu là **`19051995`**.
    * M241–M280 (`admin 2`): Mật khẩu là **`19051995`**.
  - **Triệu chứng nhận diện sai mật khẩu:**
    * Aruba AP Controller log (`show log system`): `AP ...: Client <MAC>: authenticate fail because integrity check failure in encrypted message` (Lỗi Message Integrity Check - MIC trong bắt tay 4 bước WPA2).
    * Android logcat (`wpa_supplicant` / `WifiStateMachine`): `CTRL-EVENT-ASSOC-REJECT status_code=1` kèm `DISABLED_BY_WRONG_PASSWORD` -> đẩy supplicant về `UNINITIALIZED` / `DISCONNECTED`.
  - **Cạm bẫy Android 8 Samsung S7 (SM-G930F):** Lệnh `cmd wifi` không tồn tại trên Android 8. BẮT BUỘC dùng `com.steinwurf.adbjoinwifi/.MainActivity` với tham số `--es ssid "<SSID>" --es password_type WPA --es password "<PASS>"` (sau khi đã purge Net ID sai cũ bằng `service call wifi 14 i32 <ID>`).
  - **Module Path của `operator_device_lock`:** Nằm trong `automation_core.device_lock` (`D:/Taadaa/automation-core/src`). Mọi thao tác can thiệp thiết bị bắt buộc bọc trong `operator_device_lock(machine=N, serial="<SERIAL>")` và kèm cờ `-s <serial>` trong mọi lệnh ADB.

- **Bắt buộc có Circuit Breaker cho Auto-Healer (Chống Flapping Loop):**
  CẤM TUYỆT ĐỐI các script auto-healer chạy chu kỳ ngắn (như 5 phút một lần) liên tục dập nhả `svc wifi disable && svc wifi enable` khi máy chưa có IP. Vòng lặp dập nguồn liên tục sẽ đẩy chip Broadcom PCIe vào trạng thái ngủ sâu (`state DORMANT / NO-CARRIER`, `UNINITIALIZED`), đồng thời kích hoạt Aruba AP từ chối kết nối (`ASSOCIATION_REJECTION counter:8`). Healer bắt buộc có Circuit Breaker: tối đa 2 lần thử trong 30 phút, nếu thất bại phải tạm dừng ít nhất 60 phút để máy tự ổn định stack mạng.

- **Bẫy phân quyền Knox trên ADBJoinWifi với Net ID rác:**
  Khi thiết bị đã có sẵn profile rác hoặc profile cũ (ví dụ Net ID 0 `kibe` NONE), app `com.steinwurf.adbjoinwifi` chạy dưới UID 10179 sẽ bị Knox chặn cập nhật: `UID 10179 does not have permission to update configuration`. Bắt buộc phải xóa Net ID rác qua `service call wifi 14 i32 <net_id>` từ ADB shell (UID 2000) trước khi nạp intent SSID/WPA chuẩn.

- **Suy hao vật lý 5GHz & Link Speed tụt sàn 6 Mbps trên kệ sắt:**
  Nếu máy đã xác thực WPA2 (`Supplicant state: COMPLETED`) nhưng bị rớt IP hoặc báo `CMD_IP_REACHABILITY_LOST`: kiểm tra `Link speed` trong `mWifiInfo`. Nếu link speed tụt sàn xuống 6 Mbps (RSSI <= -72 dBm do bị lưng máy tì sát vào thanh sắt kim loại của kệ), gói tin DHCP/ARP có thể bị drop. Tuy nhiên, **không được mặc định quy nguyên nhân cho hướng đặt máy**, đặc biệt khi thiết bị đã ở rất gần AP hoặc RSSI đã tốt (ví dụ khoảng -63 dBm). Khi đó phải kiểm tra theo thứ tự: (1) trạng thái hiện tại có thực sự associate không (`SSID/BSSID`, `Supplicant`, `wlan0`, IP/route), (2) profile/Net ID có xung đột hoặc bị blacklist không, (3) log association/DHCP có rejection không, rồi mới dùng thay đổi vị trí như một thử nghiệm RF có kiểm soát. Chỉ khi có bằng chứng RSSI yếu hoặc thay đổi vị trí làm link rate cải thiện ổn định mới kết luận do vật lý. TUYỆT ĐỐI CẤM tăng công suất AP Aruba lên 12–15 dBm vì sẽ gây bão hòa bộ thu (Receiver Desensitization) và kickout hàng loạt 39 máy xung quanh.

- **Anti-blame orientation gate:** Khi người vận hành phản biện rằng máy đã gần AP, không được tiếp tục lặp lại giả thuyết “đổi hướng/nhấc máy”. Thừa nhận giả thuyết đó chưa được chứng minh và chuyển sang read-only state triage. So sánh với một máy khỏe trên cùng AP, rồi phân biệt rõ `UNINITIALIZED/<unknown ssid>/IP trống` (association/profile/state failure) với `COMPLETED + IP có + 6 Mbps` (RF/rate issue). Không báo “ổn định” nếu readback hiện tại vẫn cho thấy `SSID: <unknown ssid>`, `BSSID: <none>`, `Supplicant: UNINITIALIZED` hoặc IP trống.

- **Kỷ luật can thiệp máy đơn lẻ mất Wi-Fi khi farm đang chạy ca nuôi:**
  Khi một máy đơn lẻ bị mất kết nối Wi-Fi (`IP: none`, `wlan0 state DORMANT`), máy đó không thể chạy automation và không gây ảnh hưởng tới các máy khác trên cùng rack. CẤM Coordinator vin cớ "ca nuôi đang chạy sợ ảnh hưởng máy khác" để trì hoãn xử lý. Thao tác ADB qua `operator_device_lock(machine=N, force_preempt=True, bypass_proxy_readiness=True)` diễn ra độc lập trên máy đó.

- **Khôi phục DHCP sau khi dọn sạch cờ phạt và xung đột ARP:**
  Sau khi dịch chuyển máy cải thiện RF và purge toàn bộ profile lỗi/cờ phạt `ASSOCIATION_REJECTION`/`DHCP_FAILURE` trên Android S7, nếu MikroTik vẫn lưu ARP stale dạng `status: failed` hoặc dải cũ, cần dọn ARP stale trên MikroTik (`DELETE /rest/ip/arp/<id>`) để Gateway và Client bắt tay lại hoàn tất việc cấp phát IP `192.168.110.x`.
- **Bẫy Độ Trễ Báo Cáo Watchdog & Quy Trình Triage O(1) "Mất kết nối Wi-Fi":**
  Khi User nhận Farm Alert từ watchdog báo "Mất kết nối Wi-Fi (AP)" trên một nhóm máy và hỏi lý do:
  1. TUYỆT ĐỐI CẤM vội kết luận máy đang rớt mạng hoặc hỏng Wi-Fi phần cứng.
  2. BẮT BUỘC chạy ngay lệnh trích xuất O(1) `python D:/Taadaa/tools/inspect_machine.py <N>` để đọc trạng thái thời gian thực (`wlan0 IP`, proxy, screen state).
  3. Nếu máy hiện tại đang có IP `192.168.110.x` và Proxy thông:
     - Khẳng định ngay máy không bị hỏng phần cứng và hiện tại đang bình thường.
     - Giải thích rõ cơ chế 2 tầng:
       (a) Báo cáo Watchdog là Delayed Aggregation, phản ánh thời điểm bắt đầu ca (ví dụ 06:00 sáng), trễ vài tiếng so với thời điểm gửi tin nhắn tổng hợp.
       (b) Lúc bắt đầu ca khi đánh thức máy từ trạng thái Sleep/Dozing, chip Broadcom của Samsung S7 cần 5–7 giây để bắt tay WPA2 và nhận DHCP lease từ AP Aruba. Nếu `vpn_preflight` probe quá sớm (<4s), Fail-Closed Shield sẽ ngắt phiên của máy đó để bảo vệ tài khoản (chống rò rỉ IP direct ra ngoài).
- **Broadcom PCIe wlan0 DORMANT / NO-CARRIER sau Association Rejection & Level 2 Reboot (2026-10-20):**
  Khi máy đã purge sạch profile rác (`service call wifi 14`), nạp lại SSID chuẩn và hoàn tất bắt tay 4 bước (`Key negotiation completed`, `CTRL-EVENT-CONNECTED`), nhưng `ip addr show wlan0` vẫn kẹt cứng ở `<NO-CARRIER, ... state DORMANT>` và không nhận DHCP IP: Radio toggle mềm (`svc wifi disable/enable`) không thể đánh thức PCIe bus. CẤM loop reconnect làm tăng counter association rejection phía AP. BẮT BUỘC kích hoạt Level 2 hardware-bypass reboot:
  ```bash
  python D:/Taadaa/tools/recover_stuck_s7.py --machine <N> --reboot
  ```
  Lệnh này reset cứng Broadcom chip, xóa sạch cờ phạt in-memory và cho phép supplicant + DHCP client bắt tay hoàn chỉnh khi khởi động lại. Cần lưu ý các watchdog nền (như rolling rename) có thể cạnh tranh lock; kiểm tra liveness PID trước khi xử lý lock.

## Production Automation Scripts
- `D:/Taadaa/tools/scan_rogue_wifi_farm.py`: Fast non-intrusive pre-scan script across both clusters (Dual-Cluster Farm) to audit rogue Wi-Fi networks, active SSIDs, and IP assignment across all attached devices in ~10s without modifying state or blocking on write locks.
- `D:/Taadaa/tools/batch_clean_farm_wifi.py`: Parallel locked cleanup across Dual-Cluster Farm (M1-80 & M201-280, max_workers=20), removing rogue networks (`Dat`, `Dat-1`, `BOX`, `Green Media 5G`, `admin`, `kibe`) and enforcing pure Aruba SSID binding with DHCP.
- **ADB Binary Path Invariant**: Always prefer `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`. Avoid paths containing parentheses such as `C:\Program Files (x86)\...` which trigger Hermetic Shell Guard false-positives on subshell parenthesis syntax `(...)`.
- **Subagent Delegation Contract**: When delegating Wi-Fi rescue or device cleanup to subagents, avoid `TASK_KIND: INVESTIGATE` if device mutation or script execution is expected (as `INVESTIGATE` enforces strict `[READ-ONLY WORKER]` guards). Launch `batch_clean_farm_wifi.py` directly via `terminal(background=True, notify_on_complete=True)` from Coordinator.
- **`farm_network_gate.py` Execution Timeout Window (60–90s)**: Applying profile via `farm_network_gate.py <N> --force-preempt` executes APK verification/installation, intent re-join, DHCP lease polling (up to 30s) and proxy reachability probing. The full execution lifecycle routinely takes 70–90s. Coordinator MUST NOT run `farm_network_gate.py` in foreground with default `timeout <= 60s` (which triggers exit code 124 timeout kill); ALWAYS launch via `terminal(background=True, notify_on_complete=True, timeout=180)`.
- **False 'Wi-Fi Fixed' Trap via Poison SSID `Dat`**: Connecting a farm device (e.g. M7) to a non-farm network (`Dat` broadcast by Ruijie gateway) creates an illusion of recovery (good RSSI, temporary IP). Once Ruijie Wi-Fi is disabled per RF governance, the phone is left stranded with `NO-CARRIER / DORMANT`, re-triggering `ASSOCIATION_REJECTION` on `kibe 1` because conflicting Net IDs were left in `Configured networks`. Remediation MUST purge all rogue Net IDs via `service call wifi 14 i32 <id>` and strictly bind to the canonical Aruba SSID (`kibe 1` with password `23102025` for M1–M40).

## Reference

- See `references/wifi-wrong-password-aruba-mic-failure-and-farm-profiles-20261018.md` for WPA2 integrity check failure (MIC failure), farm wifi profiles password mapping (23102025 vs 19051995), Android 8 adbjoinwifi vs cmd wifi limits, and operator_device_lock module path.
- See `references/aruba-integrity-check-failure-and-cluster-password-desync.md` for WPA2 integrity check failure (MIC failure), cluster password desync between AP groups, and clean Net ID re-binding.
- See `references/korean-firmware-binder-permission-and-static-ip-trap.md` for firmware variant differences (G930F vs G930S), SecurityException mechanics, and Static IP remediation.
- See `references/validated-rogue-ssid-canary.md` for the Android 8 binder transaction and read-back evidence pattern from the validated canary. This reference deliberately omits credentials and machine-specific secrets.
- See `references/runner-preflight-wifi-fallback-and-roam-triage.md` for the feed runner preflight credentials fallback failure (`FARM_WIFI_PROFILES_FILE`) and rogue SSID roam proxy outage root causes.
- See `references/samsung-korean-rom-wifi-saved-network-ui-trap.md` for Samsung Korean ROM (SM-G930S) Saved Networks UI hiding mechanics, shell permission denial limits, and the `OPERATOR_PREEMPT` lock takeover protocol.
- See `references/operational-closeout-gate-rubric.md` for the mandatory 4-pillar artifact requirements (raw logcat proof, 100% farm device accounting, automated pytest suite, timeline isolation) to pass `closeout_gate.py --input` with Sol Auditor (>= 85 pts APPROVED).
- See `references/auto-healer-flapping-and-broadcom-rf-desensitization.md` for Broadcom PCIe sleep loops from flapping auto-healers, Knox adbjoinwifi permission traps with stale Net IDs, physical 6Mbps floor remediation on metal racks, and why increasing Aruba Tx power breaks farm RF.
- See `references/feed-session-triage-and-liveplay-stuck-recovery.md` for feed-session failures triage, USB transport drops (M10, M30, M50), and stuck `LivePlayActivity` / `SparkActivity` recovery with `recover_stuck_s7.py`.
- See `references/wlan0-dormant-no-carrier-and-broadcom-reboot-triage-20261020.md` for wlan0 stuck in NO-CARRIER / DORMANT state after association rejection purge, Broadcom PCIe driver recovery, and escalating to Level 2 `recover_stuck_s7.py --reboot`.
- See `references/aruba-ap-zombie-session-assoc-reject-and-watchdog-delay-20261020.md` for Aruba AP zombie client session (`0.0.0.0 NOFP`), association rejection `status_code=1` triage on AP vs phone, and watchdog ca timing delay mechanics.
- See `references/dual-cluster-wifi-preflight-fallback-and-adbjoinwifi-triage.md` for dual-cluster mapping workbook fallback (`kibe` <-> `admin`) in `vpn_preflight.py` to prevent skipping Stage 2 `adbjoinwifi` auto-recovery.
- See `references/wifi-combo-systemui-false-positive-and-dhcp-timing-20261028.md` for the SystemUI `wifi_combo` false-positive trap in `_switcher_offline_reason`, Android HTTP proxy captive-portal delay, and Samsung S7 DHCP wake-up window triage.
