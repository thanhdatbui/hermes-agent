# Avatar Hook sau Registration SUCCESS (social_reg_v1.py)

## 1. Vị trí & Luồng Hook
- **Vị trí gọi:** Nằm trong `ensure_profile_completed_and_track()` sau khi lưu tracking thành công (`upsert_tracking_account` hoặc `write_deferred_tracking_result`) và trước `_post_reg_cleanup()`.
- **Feature Flags:**
  - Env: `TIKTOK_REG_AVATAR_AFTER_REG` (mặc định enabled: `!= "0"`).
  - CLI: `--no-avatar-after-reg` (bỏ qua hook nếu có cờ này).

## 2. Nguồn Avatar & Quy tắc Mapping Thư mục
- **Nguồn avatar DUY NHẤT:** `D:\TIKTOK-videonuoinick\<Folder>\avatar.jpg`.
  - Tuyệt đối KHÔNG lấy avatar từ `D:\video goc` (đây là thư mục video gốc/render source, không phải output chuẩn cho farm).
  - Nếu file `avatar.jpg` không tồn tại: log `⚠ [AVATAR] AVATAR_SOURCE_MISSING: ...` và bỏ qua (bypass), KHÔNG throw Exception làm fail quy trình reg thành công của account.
- **Mapping Thư mục Video theo Slot Máy (`stt`):**
  - Đọc từ master workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`).
  - Row tính toán: Mỗi máy `m` sở hữu 8 slot liên tiếp:
    - Slot 7 = `(m - 1) * 8 + 7` (tương ứng row data trong sheet).
    - Slot 8 = `(m - 1) * 8 + 8`.
  - Cột Folder Video trong sheet cung cấp ID thư mục cần lấy avatar.
  - Lưu ý: Hiện tại các file `Tik7.xlsx` / `Tik8.xlsx` KHÔNG tồn tại trên đĩa — KHÔNG tự ý tạo file workbook mới; chỉ log info.

## 3. Safe Execution Checklist
- Khi thực thi đổi avatar sau reg:
  - Giữ nguyên lock máy (`device_lock`) trong suốt quá trình.
  - Kiểm tra xem app TikTok có đang ở màn hình Profile / Edit Profile hay không.
  - Sau khi kết thúc đổi avatar (hoặc bypass do thiếu avatar), tiếp tục chạy qua `run_warmup_feed()` nếu có flag feed, rồi gọi `_post_reg_cleanup()`.
