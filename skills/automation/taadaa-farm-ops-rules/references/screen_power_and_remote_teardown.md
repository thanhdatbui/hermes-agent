# QTI-01: Phục hồi Screen Power Timeout & Remote ADB Teardown trên Farm

## 1. Hiện tượng & Root Cause
### Hiện tượng:
- Thiết bị cả 2 cụm (Kibe Local máy 1-100, Admin Remote máy 201-300) sau khi chạy session hoặc gặp lỗi giữa chừng thì màn hình sáng liên tục không tự tắt sau 10 phút.
- Ứng dụng TikTok bị treo ở Splash/Feed/Profile trên máy rảnh mà không tự đóng về Home.

### Root Cause:
1. **Integer.MAX_VALUE Screen Timeout:**
   - APK test của `uiautomator` (hoặc `atx-agent` khi inspect UI / dump XML) tự động gọi:
     `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức `2147483647` ms ~ 24.85 ngày) để chống tắt màn hình trong lúc automation đang tương tác.
   - Nếu runner chỉ cấu hình `screen_off_timeout = 600000` ở đầu phiên (`device_prepare.py`) mà khối teardown cuối phiên (`finally:`) không gán trả lại `600000`, thiết bị sẽ vĩnh viễn bị ghim timeout 25 ngày.
2. **Missing Remote ADB Host trong Teardown Fallback:**
   - Khi `child_ctx.adb` bị lỗi hoặc timeout, hàm `_force_stop_tiktok_and_home` rơi vào fallback gọi subprocess `adb -s <serial> shell ...`.
   - Với các máy Admin Remote (`machine >= 200`), lệnh ADB local trên máy Kibe không tìm thấy thiết bị nếu thiếu cờ `-H 192.168.110.119 -P 5037`. Lỗi bị nuốt trong `except Exception: pass`, dẫn đến app TikTok bị bỏ mặc không đóng về Launcher.

---

## 2. Invariant Teardown Contract (Bắt buộc trong mọi Runner)
Mọi hàm kết thúc phiên (kể cả thành công, timeout, hay exception) bắt buộc chạy đủ 5 lệnh chuẩn hóa:
```python
teardown_cmds = (
    ["am", "force-stop", target_package],
    ["input", "keyevent", "3"],
    ["svc", "power", "stayon", "false"],
    ["settings", "put", "global", "stay_on_while_plugged_in", "0"],
    ["settings", "put", "system", "screen_off_timeout", "600000"],
)
```

Nếu dùng ADB subprocess fallback:
```python
base_cmd = [resolved_adb]
if (machine is not None and machine >= 200) or os.environ.get("ADB_SERVER_SOCKET"):
    base_cmd.extend(["-H", "192.168.110.119", "-P", "5037"])
base_cmd.extend(["-s", serial, "shell"])
```

---

## 3. Công cụ Watchdog & Heal Nóng Hiện Trường
File công cụ chuẩn hóa máy nhàn rỗi toàn farm:
`D:/Taadaa/tools/farm_idle_screen_and_app_healer.py`
(Đồng bộ tại: `~/AppData/Local/hermes/scripts/farm_idle_screen_and_app_healer.py`)

Nguyên lý:
1. Đọc device locks (`~/.codex/device-locks/`): Bỏ qua máy đang bận (active PID).
2. Với máy rảnh:
   - Kiểm tra `screen_off_timeout` và `stay_on_while_plugged_in`, nếu sai lệch thì lập tức set về 600000ms và stayon false.
   - Kiểm tra `dumpsys window`: Nếu focus chứa `com.ss.android.ugc.trill` thì `am force-stop` và bấm `input keyevent 3` về HOME.
3. Đã đăng ký cronjob watchdog chạy định kỳ 15 phút (`farm-idle-screen-and-app-healer`).
