# Hotmail/Outlook Batch Login Device Lock Safety & Focus Isolation

## 1. Device Lock Isolation Invariant
- **Vấn đề:** Trong các script batch nạp/login Hotmail vào Outlook (`run_batch_login_xml.py`, `run_batch_login_locked.py`), nếu cấu hình `DeviceLock` với `allow_takeover=True` hoặc `takeover_authorized=True`, script sẽ cưỡng chế chiếm quyền (takeover) ngay cả khi máy đang được cron nuôi acc (`multi-machine-feed-session`) hay tiến trình khác vận hành.
- **Hậu quả:** Khi script Outlook gửi lệnh `am start` mở `com.microsoft.office.outlook`, giao diện Outlook lập tức nhảy đè lên màn hình TikTok đang chạy feed/profile preflight. Cron nuôi acc dump trúng XML của Outlook -> không thấy node `@username` -> dừng phiên và báo lỗi sai: `profile account mismatch and profile username/display name anchor is unavailable`.
- **Quy tắc bắt buộc:**
  1. Trong toàn bộ script batch login Hotmail/Outlook tự động: **CẤM đặt `allow_takeover=True` và `takeover_authorized=True`**.
  2. Bắt buộc dùng `acquire_device_lock(user_authorized=False)` tiêu chuẩn. Nếu máy đang có tiến trình khác active giữ lock -> **Safe-Skip** máy đó, ghi log rõ ràng và chuyển sang máy tiếp theo.

## 2. Post-Login App Cleanup & Foreground Release
- Sau khi hoàn thành đăng nhập (dù `SUCCESS`, `WRONG_PASSWORD` hay `UNKNOWN_SCREEN`), script bắt buộc phải giải phóng foreground:
  ```bash
  adb -s <serial> shell am force-stop com.microsoft.office.outlook
  adb -s <serial> shell input keyevent 3  # KEYCODE_HOME
  ```
- Tuyệt đối không để app Outlook hoặc onboarding sheet treo trên foreground thiết bị sau khi kết thúc lượt thao tác.

## 3. Chẩn đoán khi Cron nuôi acc báo Mismatch do App ngoài chiếm quyền
- Khi nhận cảnh báo `profile account mismatch and profile username/display name anchor is unavailable` từ `feed-session-smoke`:
  1. Kiểm tra log `focused_package` và XML của step `profile_preflight_switch_anchor_1_guard` hoặc `profile_preflight_identity_guard`.
  2. Nếu `focused_package` là `com.microsoft.office.outlook` (hoặc app ngoài khác), đây là lỗi **Focus Lost / Foreground Interception do batch chạy chéo**, không phải lỗi tài khoản TikTok hay dữ liệu workbook.
