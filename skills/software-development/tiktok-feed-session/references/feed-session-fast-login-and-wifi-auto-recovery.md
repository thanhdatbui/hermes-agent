# Feed Session: Fast Auto-Login Parent Lock & Wi-Fi Dead Service Auto Reboot (2026-09-23)

## 1. Fast Auto-Login Parent Lock Inheritance
- **Hiện tượng lỗi:** Khi feed-session phát hiện tài khoản chỉ định vắng mặt trong Account Switcher (`manual-needed:account-switcher-missing-expected`), script gọi `tiktok_login_v1.py` để nạp bù nhanh.
- **Xung đột lock:** `run_tiktok.py` (project `tiktok-luot nuoi acc`) đang nắm giữ file lock thiết bị `machine_N.lock.json`. `tiktok_login_v1.py` khởi chạy phát hiện lock mẹ liền raise `DeviceLockNeedsUserDecision` và văng exit code 2.
- **Giải pháp:**
  * `tiktok_login_v1.py` hỗ trợ argument `--allow-parent-lock` và kiểm tra `PARENT_LOCK_PROJECTS = ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session")`. Nếu match, gán lease `InheritedDeviceLock` thay vì abort.
  * `feed_swipe_smoke.py` trong `_run_fast_targeted_login` bổ sung `"--allow-parent-lock"` vào `fast_cmd`.

## 2. Wi-Fi Dead Service Auto Reboot (`vpn_preflight.py`)
- **Hiện tượng lỗi:** Máy farm báo `dumpsys connectivity: Wi-Fi not connected` hoặc `wlan0: state DOWN` dù proxy ngoài còn sống 100%. Lệnh `dumpsys wifi` báo `Can't find service: wifi` hoặc exit code 135/139 do tiến trình Android Framework `system_server` crash ngầm.
- **Giải pháp tự động hóa trong `require_proxy_connected`:**
  * Tầng 1: Thử `svc wifi enable` và kiểm tra lại `check_android_vpn`.
  * Tầng 2: Nếu phát hiện service dead (`Can't find service` hoặc exit code 135/139), script tự động phát lệnh `adb reboot`, đồng bộ `wait-for-device` + polling `getprop sys.boot_completed == 1` trong 90s, sau đó re-verify Wi-Fi.
  * Cờ `_wifi_reboot_attempted` đảm bảo mỗi máy chỉ reboot tối đa 1 lần/phiên preflight, fail-closed an toàn nếu phần cứng hỏng thật.
