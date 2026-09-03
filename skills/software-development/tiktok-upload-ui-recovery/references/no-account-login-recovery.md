# NO_ACCOUNT_LOGIN_REQUIRED / LOGIN_RECOVERY_REQUIRED Pattern (2026-09-01)

## Hiện tượng
- Khi `tiktok-video` mở app và navigate vào tab Hồ sơ để chuyển đổi tài khoản (Account Switcher), màn hình Hồ sơ rỗng không có nick nào đăng nhập (chỉ có text *"Đăng nhập vào tài khoản hiện có"* và nút *"Đăng nhập"* màu đỏ/hồng).
- Runner không thể tìm thấy anchor Switcher hoặc username hiện tại.

## Log / Mã lỗi nhận diện
- `[ACCOUNT_SWITCHER_FAILED] PROFILE_ROOT_STALE: TikTok returned to feed before switcher preparation. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa`
- `[EDGE] No-account login surface detected; reserving tiktok_login recovery`
- `report.json` trả về:
  ```json
  {
    "status": "LOGIN_RECOVERY_REQUIRED",
    "device_id": "<serial>",
    "reason": "[NO_ACCOUNT_LOGIN_REQUIRED] TikTok đang ở Hồ sơ rỗng với nút Đăng nhập. Cần chạy login recovery handler rồi recapture trước khi retry upload.",
    "last_state": "MANUAL_REVIEW",
    "recovery_handler": "tiktok_login"
  }
  ```

## Quy tắc xử lý an toàn
1. **Giữ hiện trường & Lock thiết bị**:
   - Khóa lock thiết bị ở trạng thái `blocked` (`owner_active: false`) trong `~/.codex/device-locks/machine_<N>.lock.json` và `serial_<serial>.lock.json` để cron không chạy đè.
2. **Không tap mù**:
   - Tuyệt đối không fallback bấm tọa độ Switcher khi màn hình ở trạng thái unauthenticated.
3. **Phục hồi qua `tiktok-log-in`**:
   - Cần kích hoạt runner `tiktok-log-in` để đăng nhập lại các nick được phân bổ cho máy trong `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx` trước khi kích hoạt lại flow upload/feed.
