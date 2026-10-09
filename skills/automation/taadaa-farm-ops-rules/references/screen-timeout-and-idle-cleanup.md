# Screen Timeout Hijack Prevention & Idle App Cleanup

## 1. Triệu chứng & Hiện trường Thực tế
- Toàn bộ hoặc hàng loạt máy farm (cả Kibe lẫn Admin) sáng rực màn hình, không tự tắt sau 10 phút nhàn rỗi.
- Pin nóng, hao pin, có nguy cơ chai phồng pin hoặc ám màn hình AMOLED.
- Kiểm tra hiện trường O(1) qua ADB:
  - `settings get system screen_off_timeout` trả về **`2147483647`** (thay vì chuẩn farm `600000` = 10 phút).
  - `2147483647` chính là `Integer.MAX_VALUE` = ~24.85 ngày (~25 ngày).
  - `dumpsys power` báo: `Looper state: Message 0: { when=+24d18h... what=1 }` -> Android hẹn 25 ngày nữa mới tắt màn hình!
  - App TikTok (hoặc camera/splash) bị ngâm ở foreground nhiều giờ sau khi ca nuôi kết thúc.

## 2. Nguyên nhân Gốc rễ
1. **Thủ phạm ghi đè:**
   - Khi chạy flow nuôi feed, auto-login hoặc recovery, hệ thống gọi `uiautomator` dump XML hoặc kích hoạt stub test APK của `atx-agent`.
   - Mã nguồn Java của `uiautomator` test runner có cơ chế mặc định tự gọi:
     `Settings.System.putInt(..., Settings.System.SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)`
     để ngăn Android tắt màn hình làm đứt phiên automation.
2. **Lỗ hổng Teardown:**
   - Hàm `configure_device_screen_stay_on` (đặt 10 phút) chỉ được gọi lúc chuẩn bị bắt đầu phiên (`device_prepare.py`).
   - Nhưng trong quá trình chạy, `uiautomator` đã âm thầm đổi thành 25 ngày.
   - Khi phiên kết thúc (khối `finally:` teardown trong `multi_machine_feed_session.py`), code thiếu bước set trả lại `600000`.
3. **Lỗ hổng Remote ADB trên cụm Admin (Máy >= 200):**
   - Khi teardown fallback được gọi qua `_force_stop_tiktok_and_home`, lệnh `subprocess.run` thiếu `-H 192.168.110.119 -P 5037`.
   - ADB cục bộ trên Kibe không tìm thấy thiết bị Admin -> fallback fail ngầm -> app TikTok không được đóng về HOME.

## 3. Quy tắc Khắc phục & Tiêu chuẩn Teardown Bắt buộc
Mọi script/runner can thiệp thiết bị (Feed session, Follow, Reg, Login, Avatar) trong khối `finally: teardown` BẮT BUỘC thực hiện:
```python
teardown_cmds = (
    ["am", "force-stop", target_package],
    ["input", "keyevent", "3"],                             # HOME
    ["svc", "power", "stayon", "false"],
    ["settings", "put", "global", "stay_on_while_plugged_in", "0"],
    ["settings", "put", "system", "screen_off_timeout", "600000"],  # 10 phút
)
```

Khi chạy fallback qua `subprocess.run`, nếu `machine >= 200` hoặc có `ADB_SERVER_SOCKET`, bắt buộc chèn:
`["-H", "192.168.110.119", "-P", "5037"]`.

## 4. Công cụ Watchdog Tự động Dọn dẹp (`farm_idle_screen_and_app_healer.py`)
- Định kỳ quét các thiết bị online trên cả Kibe Local và Admin Remote.
- Kiểm tra lock an toàn: Bỏ qua máy đang có job chạy (có file lock trong `~/.codex/device-locks/` với PID active).
- Với các máy RẢNH:
  - Nếu `screen_off_timeout != 600000` hoặc `stay_on != 0` -> khôi phục ngay lập tức.
  - Nếu `mCurrentFocus` chứa `com.ss.android.ugc.trill` -> `am force-stop` và bấm HOME.
