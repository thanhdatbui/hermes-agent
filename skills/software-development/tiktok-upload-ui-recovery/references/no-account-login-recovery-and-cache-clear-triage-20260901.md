# Triage Văng Sạch Account / NO_ACCOUNT_LOGIN_REQUIRED & Xác Minh Cache Clean

## Hiện tượng
Trong flow upload video TikTok (`Tiktok-video` / Tik1/Tik2/Tik3), runner dừng phiên với lỗi:
- `upload_subprocess_nonzero`
- `LOGIN_RECOVERY_REQUIRED`
- `[NO_ACCOUNT_LOGIN_REQUIRED] TikTok đang ở Hồ sơ rỗng với nút Đăng nhập. Cần chạy login recovery handler rồi recapture trước khi retry upload.`
- Màn hình TikTok rơi về Profile khách (Guest) hiển thị "Đăng nhập vào tài khoản hiện có", mất toàn bộ session tài khoản trên máy.

## Quy trình đối chiếu nguyên nhân (Triage Checklist)

1. **Kiểm tra Pre-cache Cleanup trong runner Upload:**
   - Đọc `D:\CodexRuntime\tiktok-video\runs\<run_id>\execution.log`.
   - Xác nhận log: `[INFO] scripts.tiktok_workflow.state_machine: === PRE_CACHE_CLEANUP ===` kèm `Skipping cache maintenance; preserve the authenticated TikTok session`.
   - Khẳng định runner upload không tự động clear cache/data làm mất tài khoản.

2. **Kiểm tra Invariants cấm `pm clear` toàn farm:**
   - Toàn bộ repos farm (`Tiktok-video`, `tiktok-luot nuoi acc`, `Tiktok_Reg`, `automation-core`) đều cấm lệnh `pm clear` và có test guard `test_no_adb_cache_commands.py` chặn.

3. **Kiểm tra Cron dọn cache cuối ngày (`cron_clear_tiktok_cache.py` - 04:00 AM):**
   - Script chạy qua Deep Link intent `snssdk1180://clean_cache` (hoặc widget Home) -> mở trang "Giải phóng dung lượng" -> bấm nút UI "Xóa" bên cạnh "Bộ nhớ đệm".
   - Đây là cơ chế in-app an toàn, không xóa app data hay session login.
   - Nếu máy không mở được UI storage, cron log `WIDGET_MISS` và bỏ qua.

4. **Truy vết lịch sử thêm/đổi nick gần nhất trên máy:**
   - Đọc `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` hoặc artifacts trong `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\...`.
   - Tìm thời điểm gần nhất mở dropdown Switcher (`[3] Open account dropdown`): kiểm tra xem các nick cũ có còn hiển thị không.
   - Kiểm tra xem sau khi đăng ký nick mới (thứ 5, 6...) có xảy ra xung đột session hoặc TikTok server force logout toàn bộ danh sách tài khoản liên kết hay không.

5. **Nguyên nhân gốc rễ phổ biến:**
   - TikTok server thu hồi phiên (revoke session token) khi phát hiện dấu hiệu bất thường (đổi IP/proxy đột ngột, checkpoint bảo mật của 1 nick trong cụm, hoặc vượt ngưỡng tài khoản cho phép trên app).
   - TikTok app crash / corrupted local SQLite DB khi restore subpage dẫn đến app tự reset session về trạng thái Guest.
