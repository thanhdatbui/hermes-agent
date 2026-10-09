# Quy tắc Vòng đời Profile GPMLogin & Dọn dẹp Thiết bị S7 Tự động

## 1. Vấn đề gốc rễ (Root Cause)
- Khi chạy tự động login Google / nạp OAuth vào GPMLogin, watchdog ca tối thường bị nghẽn (chỉ chọn được 2-3 máy) do:
  1. Hơn 100+ Gmail trong `master_gmail_manager.xlsx` chưa từng được tạo profile trong GPMLogin DB.
  2. Nhiều profile cũ chứa tài khoản Google đã bị `DIE` / `BAN` / `SUSPENDED` nhưng vẫn chiếm tài nguyên ổ đĩa và danh bạ GPM.
  3. Trên thiết bị S7 thật, các Gmail `DIE` vẫn nằm kẹt trong Android OS (`android.settings.SYNC_SETTINGS`), gây tràn trần 4-5 tài khoản Google/máy, cản trở việc đăng ký Gmail mới và làm kẹt Google Prompt.

## 2. Quy trình Quản lý Vòng đời 2 Chiều (GPM + S7)

### A. Tự động dọn & tạo trên GPMLogin PC (`sync_lifecycle_gpm`)
- **Dọn dẹp (Clean DIE)**: Quét các tài khoản có trạng thái `DIE`, `BAN`, `SUSPENDED` từ Master Excel. Tìm các profile tương ứng trong SQLite `profile_data.db` và gọi API:
  `GET http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=2` (xóa cả thư mục profile trên ổ cứng).
- **Tạo mới (Create LIVE)**:
  - Chỉ lọc các tài khoản có trạng thái `LIVE`, không dính recovery `khoale`, không nằm trong blacklist checkpoint (`oauth_pipeline_status.json`).
  - Kiểm tra thiết bị S7 tương ứng bắt buộc phải **đang online ADB** (`adb devices`).
  - Gán đúng proxy 4G chuẩn từ `PROXYgandienthoai.xlsx` (`test.taadaa.click:PORT:user:pass`).
  - Định dạng tên profile: `{mid:02d} - {email} - {port}`.

### B. Tự động dọn Gmail DIE cuốn chiếu trên thiết bị S7 (`cleanup_s7_die_accounts`)
- **Khung giờ chạy**: **CHỈ CHẠY BUỔI SÁNG (07:15 - 08:45 HCM)** — ngay sau khi cron `daily-manual-stock-checklive` cập nhật danh sách DIE lúc 07:00, và trước khi chuỗi bật 2FA Gmail 08:30 bắt đầu. **Tuyệt đối không chạy buổi chiều**.
- **Quy tắc An toàn Ca nuôi (Manifest Preflight)**:
  - Trước khi chạm vào máy, đọc file `assignment-v1-*.json` trong `D:/Taadaa/runtime/kibe/cron-state/manifests/<today>/`.
  - Nếu máy đang nuôi TikTok hoặc sắp vào ca nuôi trong vòng 30 phút -> **Bỏ qua ngay lập tức**.
- **Cơ chế Khóa Non-blocking (`DeviceLockUnavailable`)**:
  - Dùng `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", bypass_proxy_readiness=True)`.
  - Nếu máy đang bị cron nuôi hoặc tiến trình khác giữ lock -> **Bỏ qua máy đó để sang máy rảnh dọn trước** (không sleep/chờ mù quáng).
  - Khi cron nuôi nhả lock, ở tick 15 phút tiếp theo cron dọn sẽ tự động quay lại xử lý.
- **Xác nhận thực tế qua ADB**:
  - Dùng `dumpsys account` kiểm tra tài khoản DIE có thực sự còn trên máy S7 không.
  - Nếu còn: mở Settings gỡ tài khoản (`preflight_s7_rolling_cleanup.py:remove_account_adb`).
  - Luôn gửi lệnh `input keyevent 3` (HOME) và nhả lock ngay lập tức sau khi xong từng máy.

## 3. Lịch Cronjob Chuẩn
- Cronjob: `gpm-lifecycle-sync-watchdog`
- Schedule: `*/15 7,8 * * *` (Mỗi 15 phút trong khung 07:00 - 08:45 sáng hàng ngày).
- Script thực thi: `sync_gpm_lifecycle.py`
