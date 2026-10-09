# Fast Auto-Login Parent-Lock Inheritance & Wi-Fi Dead-Service Auto Guarded Reboot (2026-09-23)

## 1. Fast Auto-Login Parent-Lock Inheritance (`--allow-parent-lock`)

### Bối cảnh & Triệu chứng lỗi
- Trong luồng nuôi acc (`feed-session-smoke` / `multi-machine-feed-session`), khi kiểm tra Account Switcher phát hiện thiếu nick mục tiêu (`manual-needed:account-switcher-missing-expected`), script kích hoạt `auto_login_recovery` qua Fast Targeted Login:
  `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --ss --allow-parent-lock`
- **Điểm nghẽn xung đột lock:** Tiến trình mẹ `run_tiktok.py` (project `tiktok-luot nuoi acc`) đang nắm giữ file lock thiết bị:
  `C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json`
- Khi `tiktok_login_v1.py` khởi chạy với `acquire_device_lock(user_authorized=False)`, nó phát hiện active lock của `run_tiktok.py` và raise `DeviceLockNeedsUserDecision`, thoát ngay với exit code 2:
  `[device-lock] NEEDS_USER_DECISION: device lock active: path=... project=tiktok-luot nuoi acc command=run_tiktok.py --mode multi-machine-feed-session reservation`
- **Hậu quả:** Fast auto-login thất bại trong 6 giây, feed session fallback sang `reconcile_tiktok_accounts.py` (vốn quét toàn bộ inventory) dẫn đến timeout 300s và toàn bộ máy bị đánh dấu `manual-needed` oan uổng dù máy còn slot trống (ví dụ 7/8 nick) và nick có sẵn pass/2FA TOTP trong workbook.

### Cơ chế & Kiến trúc khắc phục
1. **Phía `tiktok_login_v1.py`:**
   - Thêm cờ CLI `--allow-parent-lock`.
   - Danh sách allowlist parent projects: `PARENT_LOCK_PROJECTS = ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session")`.
   - Helper `_is_parent_lock_owner(exc)` trích xuất `project` và `pid` từ owner của exception.
   - Khi bắt `(DeviceLockNeedsUserDecision, DeviceLockUnavailable)`, nếu `args.allow_parent_lock` và lock thuộc `PARENT_LOCK_PROJECTS`: gán `device_lock = InheritedDeviceLock(machine=args.stt, serial=device_id)` để tiếp tục login thay vì thoát mã 2.
2. **Phía Caller `feed_swipe_smoke.py` (`_run_fast_targeted_login`):**
   - BẮT BUỘC truyền `--allow-parent-lock` trong mảng `fast_cmd`.
3. **Focused Tests:**
   - `python_runner/tests/test_fast_login_parent_lock.py`
   - `D:/Taadaa/Tiktok_Reg/tests/test_tiktok_login_parent_lock.py` (4/4 passed).

---

## 2. Wi-Fi Dead-Service Auto Guarded Reboot (Xử lý Crash `system_server`)

### Bối cảnh & Chỉ đạo Vận hành
- User chỉ đạo: *"tóm lại đang chạy mà gặp lỗi wifi thì xử lý sao ... thì handle vào script đi"*.
- **Hiện tượng:** Máy báo lỗi `dumpsys connectivity: Wi-Fi not connected` / `wlan0: state DOWN`.
- **Nguyên nhân gốc rễ:** Tiến trình hệ điều hành Android `system_server` bị crash ngầm. Lệnh `dumpsys wifi` trả về `Can't find service: wifi` hoặc lệnh `svc wifi enable` trả về exit code `135` / `139` (SIGBUS/SIGSEGV). Kernel Linux và daemon ADB qua cáp USB vẫn sống nhưng toàn bộ subsystem Wi-Fi đã chết, khiến các lệnh bật Wi-Fi mềm hoàn toàn vô hiệu.
- **Proxy Server vẫn sống 100%:** Test curl trực tiếp từ host qua proxy vẫn trả về IP bình thường.

### Cơ chế Tự phục hồi trong `python_runner/core/vpn_preflight.py` (`require_proxy_connected`)
1. **Nhận diện Dead Service:**
   ```python
   wifi_output = (str(getattr(wifi_res, "stdout", "") or "") + str(getattr(wifi_res, "stderr", "") or "")).lower()
   exit_code = getattr(wifi_res, "exit_code", getattr(wifi_res, "returncode", 0))
   is_service_dead = "can't find service" in wifi_output or exit_code in (135, 139)
   ```
2. **Tự động kích hoạt Guarded Reboot:**
   - Kiểm tra cờ loop breaker: `if is_service_dead and getattr(adb, "_wifi_reboot_attempted", False) is not True:`
   - Đánh dấu `setattr(adb, "_wifi_reboot_attempted", True)` (mỗi máy chỉ reboot tối đa 1 lần/phiên preflight).
   - Phát lệnh `reboot` và đợi `wait-for-device` (timeout 90s).
   - Polling đồng bộ `sys.boot_completed == 1`.
   - Nghỉ 5.0s cho Wi-Fi tự động liên kết (association) lại AP.
   - Re-check `check_android_vpn()`. Nếu `reboot_status.allowed` -> Trả về kết quả thành công, cho phép batch chạy tiếp mà không cần can thiệp thủ công.
3. **Focused Test:**
   - `python_runner/tests/test_vpn_preflight_router.py::TestVpnPreflightRouter::test_dead_service_triggers_guarded_reboot_and_recovers` (21/21 passed).
