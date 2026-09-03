# Case 71 (02/09/2026): Tự Động Gỡ Popup Quyền Hệ Thống (PackageInstaller) Khi Mất Focus Sau Navigation Tap (Sự Cố Máy 72)

## Context & Problem
Trong quy trình chạy nuôi nick (`multi-machine-feed-session`), sau khi app TikTok đã chạy ổn định, kịch bản thực hiện bấm chuyển tab điều hướng (ví dụ: chuyển sang tab Hồ sơ hoặc Tìm liên hệ / Bạn bè). Hành động chuyển tab này có thể kích hoạt hệ điều hành Android hiển thị popup xin quyền Danh bạ (`com.google.android.packageinstaller` / `com.android.permissioncontroller` với nội dung "Cho phép TikTok truy cập vào danh bạ của bạn?").

### Symptoms
- Phiên chạy dừng đột ngột ngay sau khi thực hiện cú tap điều hướng:
  `TikTok focus lost after navigation tap: com.google.android.packageinstaller`
- Telegram alert: `[MÁY 72] DỪNG PHIÊN • Script: multi-machine-feed-session • Tài khoản: cecilssimpso82 • Lý do: TikTok focus lost after navigation tap: com.google.android.packageinstaller • Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Ảnh chụp màn hình hiện rõ dialog xin quyền hệ thống đè lên màn hình TikTok hồ sơ/tìm bạn bè.

### Root Cause
1. Trong `flows/calibrate_screens.py` (`tap_navigation_target`), sau khi thực hiện tap tọa độ mục tiêu điều hướng, hàm gọi `post_focus = get_focused_activity(ctx)`.
2. Do dialog hệ thống xuất hiện, `post_package` trả về `com.google.android.packageinstaller` (khác `expected_package = com.ss.android.ugc.trill`).
3. Nhánh kiểm tra phục hồi trước đây chỉ xử lý các package thuộc `{"com.android.systemui", "com.sec.android.app.launcher", "com.google.android.apps.nexuslauncher"}` (bằng cách ấn BACK 1 lần).
4. Các package xin quyền hệ thống (`com.google.android.packageinstaller`, `com.android.packageinstaller`, `com.android.permissioncontroller`) bị bỏ qua, dẫn đến `recovered_focus = False`, script đánh giá là mất focus không thể phục hồi và fail-closed phiên chạy.

---

## Architectural Solution

### 1. Phục hồi Focus Sau Navigation Tap (`flows/calibrate_screens.py`)
- Định nghĩa tập package xin quyền hệ thống:
  ```python
  SYSTEM_PERMISSION_PACKAGES = {
      "com.android.packageinstaller",
      "com.google.android.packageinstaller",
      "com.android.permissioncontroller",
  }
  ```
- Mở rộng logic phục hồi trong `tap_navigation_target`:
  - Khi `post_package in SYSTEM_PERMISSION_PACKAGES`:
    - Kích hoạt `dismiss_tiktok_popups` từ `automation_core.tiktok` với callbacks `capture_xml`, `tap`, `press_back`.
    - Thực hiện flow: Tick checkbox *"Không hỏi lại"* (`check_do_not_ask_again`) nếu chưa tick -> Bấm *"TỪ CHỐI"* (Deny button).
    - Sau khi dismiss, `time.sleep(0.8)` và gọi lại `retry_focus = get_focused_activity(ctx)`.
    - Nếu focus quay trở lại TikTok (`retry_pkg == expected_package`), đánh dấu `recovered_focus = True`, ghi log `action="recover_tiktok_focus_after_permission_popup", result="success"`, và cho phép kịch bản điều hướng tiếp tục bình thường mà không trả về lỗi.

### 2. Phân biệt với Mất Focus Do Ứng Dụng Ngoài
- Nếu sau khi thử gỡ popup quyền mà focus vẫn không về lại TikTok (hoặc package lạ ngoài danh sách cho phép), quy trình mới trả về lỗi `TikTok focus lost after navigation tap: <package>`.

---

## Verification & Testing Contract
- **Unit / Flow Test (`python_runner/tests/test_calibrate_screens.py`)**:
  - `test_navigation_recovers_focus_when_permission_dialog_dismissed`: Mô phỏng `tap_navigation_target` gặp `post_package == "com.google.android.packageinstaller"`, `dismiss_tiktok_popups` chạy thành công và focus quay lại `com.ss.android.ugc.trill`, hàm trả về `NavigationResult.ok == True, status="pass"`.
  - `test_navigation_fails_closed_when_permission_dialog_not_dismissed`: Đảm bảo hành vi fail-closed an toàn khi không thể gỡ dialog quyền.
  - Toàn bộ test suite 35/35 test pass 100%.
- **Canary Kiểm Chứng Trực Tiếp Trên Máy Farm 72**:
  - Command: `python python_runner/run_tiktok.py --mode multi-machine-feed-session --account-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" --machines 72 --account-row-index 4 --recovery-test-swipes 2 --prepare-tiktok --allow-navigation-only --allow-feed-swipe --cleanup-on-stop`
  - Kết quả: `Status: success`, hoàn thành 2/2 swipes.
