# Fleet Screen Timeout Teardown & Farm App Provisioning Invariants (25/09/2026)

## 1. Cơ chế màn hình bị kẹt sáng 25 ngày & Lỗ hổng Teardown
- **Hiện tượng**: Hàng loạt máy (cả Kibe Local lẫn Admin Remote 192.168.110.119) bị sáng màn hình liên tục không tự tắt sau 10 phút, app TikTok treo ngâm từ sáng đến tối.
- **Root cause 1 (UiAutomator Stub Override)**:
  Khi runner hoặc ATX agent kích hoạt uiautomator stub để inspect cây giao diện, APK test ngầm gọi:
  `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức **`2147483647` ms ~ 25 ngày**) để chống tắt màn hình trong lúc automation đang tương tác.
- **Root cause 2 (Lỗ hổng Teardown trong code)**:
  Hàm `configure_device_screen_stay_on(600000)` chỉ được gọi 1 lần ở đầu phiên (`device_prepare.py`). Khi kết thúc phiên (kể cả hoàn thành, lỗi hay timeout), khối `finally: teardown` hoàn toàn không có bước set trả `screen_off_timeout` về 600000ms. Máy nào từng chạy stub là vĩnh viễn bị ghim timeout 25 ngày.
- **Root cause 3 (Remote ADB Timeout & Nuốt Exception)**:
  Hàm fallback `_force_stop_tiktok_and_home` dùng `subprocess.run([adb, "-s", serial...])` thiếu tham số `-H 192.168.110.119 -P 5037` cho các máy Admin (`machine >= 200`). Khi adb client chính bị timeout, fallback thất bại âm thầm trong `except Exception: pass`, app TikTok bị bỏ mặc mở nguyên xi.

## 2. Quy chuẩn Teardown Bắt Buộc Trong Codebase
Mọi runner hoặc script kết thúc can thiệp thiết bị (kể cả success, exception hay timeout) BẮT BUỘC thực thi chuỗi 5 lệnh teardown:
1. `am force-stop <package>` (dừng app)
2. `input keyevent 3` (đưa về HOME Launcher)
3. `svc power stayon false` (tắt chế độ sáng liên tục)
4. `settings put global stay_on_while_plugged_in 0` (cho phép tắt màn khi cắm sạc)
5. `settings put system screen_off_timeout 600000` (khôi phục 10 phút tự tắt màn hình)

*Lưu ý Remote Host:* Khi thao tác trên cụm Admin (`machine >= 200`), lệnh subprocess fallback bắt buộc chèn:
`-H 192.168.110.119 -P 5037`.

## 3. Quy chuẩn Tự Động Cài Bù 4 App Chuẩn Farm Cho Máy Mới / Máy Sửa Xong
- **Tư duy cốt lõi (User Invariant)**:
  1. **Linh động Package Name**: Đúng app (package name tồn tại) là được, **KHÔNG ép cứng phiên bản APK** (TikTok 46.x hay 47.x đều hợp lệ; Outlook lấy được mail là được).
  2. **Zero Manual Effort**: Máy mới lắp vào hoặc máy vừa chạy lại ROM cắm vào farm, hệ thống tự động phát hiện và cài bù khi máy rảnh.

- **Bộ 4 App Cốt Lõi**:
  1. **TikTok**: `com.ss.android.ugc.trill` hoặc `com.zhiliaoapp.musically`
     - Kho APK: `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\v47.0.3` (cài split base + configs + dex session).
  2. **Microsoft Outlook**: `com.microsoft.office.outlook`
     - Kho APK: `D:\OneDrive\apk-bank\com_microsoft_office_outlook` (cài single APK).
  3. **Xiaowei Keyboard**: `com.android.xwkeyboard`
     - Kho APK: `C:\Program Files (x86)\xiaowei\tools\XWKeyboard.apk` (cài single APK).
  4. **ATX-Agent Stubs**: `com.github.uiautomator` (kèm `.test`)
     - Kho APK: `C:\Users\Kibe\.GemPhoneFarm\app\app-uiautomator.apk` và `app-uiautomator-test.apk` (cài multi APKs).

- **Cấu hình bổ sung ngay sau khi cài đặt bù**:
  - `settings put system screen_off_timeout 600000`
  - `settings put global stay_on_while_plugged_in 0`
  - `svc power stayon false`
  - `settings put system accelerometer_rotation 0` (khóa xoay dọc)

- **Guard Chống Bẫy False-Positive ADB Timeout**:
  Khi kiểm tra package bằng `pm list packages`, nếu lệnh bị timeout hoặc stdout không chứa package hệ thống cốt lõi `"android"`, BẮT BUỘC coi là `unresponsive / adb timeout`, TUYỆT ĐỐI KHÔNG coi là `missing apps` để tránh gọi install sai đối tượng.
