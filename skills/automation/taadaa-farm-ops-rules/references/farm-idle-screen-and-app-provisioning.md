# Quy Chuẩn Idle Screen Timeout & Provisioning App Chuẩn Toàn Farm (2026-09-24)

## 1. Sự Cố Đồng Loạt Sáng Màn Hình & Treo TikTok Khi Idle
### Bản chất hiện tượng:
- Nhiều máy trên cụm Kibe Local (1-100) và cụm Admin Remote (201-300, qua `192.168.110.119:5037`) bị sáng rực liên tục không tự tắt sau 10 phút.
- App TikTok bị treo trên màn hình nhiều giờ liền không tự đóng về Home.

### Root Causes:
1. **`uiautomator` test APK stub ghi đè ngầm:** Khi kích hoạt `atx-agent` hoặc dump XML, Android stub gọi `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức `2147483647` ms ~ 25 ngày) để ngăn màn hình tắt trong khi automation đang chạy.
2. **Lỗ hổng Teardown:** Runner (`device_prepare.py`) chỉ set `screen_off_timeout 600000` ở đầu phiên. Khối `finally: teardown` trong `multi_machine_feed_session.py` không khôi phục lại timeout và `stay_on_while_plugged_in 0`.
3. **Thiếu Remote ADB Host trong fallback teardown:** Hàm `_force_stop_tiktok_and_home` khi fallback subprocess thiếu `-H 192.168.110.119 -P 5037`, khiến lệnh force-stop trên máy Admin (`machine >= 200`) thất bại và nuốt ngoại lệ.

### Giải pháp kỹ thuật chuẩn hóa:
1. **Teardown Invariant trong runner:** Bắt buộc thực hiện 5 lệnh teardown theo thứ tự:
   ```python
   teardown_cmds = (
       ["am", "force-stop", target_package],
       ["input", "keyevent", "3"],
       ["svc", "power", "stayon", "false"],
       ["settings", "put", "global", "stay_on_while_plugged_in", "0"],
       ["settings", "put", "system", "screen_off_timeout", "600000"],
   )
   ```
2. **Watchdog định kỳ `farm-idle-screen-and-app-healer` (15 phút/lần):**
   - Quét toàn bộ máy online qua `adb devices` (không phụ thuộc danh sách tĩnh).
   - Kiểm tra `device-locks`: Bỏ qua các máy đang bận (active PID).
   - Với máy nhàn rỗi: Nếu `screen_off_timeout != 600000` hoặc `stay_on != 0` -> khôi phục ngay 10m; nếu TikTok còn focus -> force stop về HOME.

---

## 2. Quy Chuẩn Kiểm Tra & Cài Đặt App Cho Máy Mới / Sửa Xong
### Yêu cầu cốt lõi từ User:
- **Tiêu chí linh động:** Chỉ cần kiểm tra đúng app (`pm list packages -3` chứa đúng package name), **KHÔNG ÉP CỨNG PHIÊN BẢN APK**.
- **Không yêu cầu thao tác thủ công:** Máy mới ráp hoặc máy sửa xong cắm vào phải tự động nhận diện và cấu hình.

### Bộ 4 App Cốt Lõi Trên Mọi Thiết Bị Farm:
1. **TikTok:** `com.ss.android.ugc.trill` (hoặc `com.zhiliaoapp.musically`).
2. **Microsoft Outlook:** `com.microsoft.office.outlook` (phục vụ flow reg Hotmail / OTP).
3. **Xiaowei Keyboard:** `com.android.xwkeyboard` (bàn phím ADB gõ tốc độ cao).
4. **ATX Agent Stubs:** `com.github.uiautomator` & `com.github.uiautomator.test` (bắt buộc cho daemon `atx-agent` cổng 7912, KHÔNG PHẢI lệnh shell uiautomator dump bị cấm).

### Bẫy Kỹ Thuật Khi Kiểm Tra Gói Cài Đặt (False-Positive Missing Apps):
- Khi thiết bị bị giật lag, màn hình tắt sâu hoặc ADB bị nghẽn lệnh, lệnh `pm list packages` có thể bị timeout hoặc trả về stdout rỗng.
- **CẤM TUYỆT ĐỐI** coi stdout rỗng là "thiết bị thiếu 100% ứng dụng" để tự ý kích hoạt quy trình cài đặt lại (sẽ gây nghẽn USB và chồng chéo tiến trình).
- **Guard bắt buộc:** Luôn kiểm tra sự hiện diện của gói lõi hệ thống `"android"`. Nếu kết quả không chứa `"android"` hoặc trả về non-zero exit code ➡️ Đánh dấu thiết bị là "ADB Unresponsive / Timeout" và bỏ qua, tuyệt đối không trigger cài đặt.

