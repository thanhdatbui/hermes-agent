# Chẩn Đoán Lỗi Runner 2FA Mã Thoát 5 (Race Condition Với Cron Sync & Thiếu Dọn Lock Admin)

## 1. Triệu Chứng Điển Hình
- Báo cáo toàn farm trả về:
  ```text
  ⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO 2FA TIKTOK CA SÁNG:
  • Farm Kibe (Máy 1-80): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0
  • Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0
  • Lỗi runner: mã thoát 5
  ```
- Hoàn tất 0 / Bỏ qua 0 / Lỗi 0: Cho thấy runner sập ngay từ `freeze_targets()` ở giai đoạn bootstrap trước khi kịp dispatch bất kỳ worker nào.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Xung đột thời gian thực với Cron Sync định kỳ 5 phút (`taikhoan-run-safe-sync`):**
   - Job `taikhoan_sync_cron_launcher.py` chạy mỗi 5 phút ghi đè `taikhoan_dat_v2_updated .xlsx` khi có thay đổi.
   - Nếu `night-tiktok-2fa-watchdog` tick đúng lúc cron sync đang ghi hoặc OneDrive client đang hydrate/upload file, `openpyxl.load_workbook()` hoặc `acquire_workbook_lock()` ném `WorkbookError` hoặc `OSError: [Errno 22]`.
   - Trong `run_batch_live_2fa.py`, `freeze_targets()` ban đầu chỉ thử mở file 1 lần duy nhất mà không có retry backoff, dẫn đến văng ngay `exit code 5`.

2. **Cụm Remote Admin-PC (Máy 201-280) thiếu cơ chế dọn lock mồ côi:**
   - Khi chạy qua SSH PowerShell trên Admin-PC, nếu phiên Excel trước đó để lại file lock rác `~$taikhoan_dat_v2_updated .xlsx`, `freeze_targets()` trên Admin văng `WorkbookError("BLOCKED_WORKBOOK_OPEN_IN_EXCEL")`.
   - Script watchdog phía Kibe có cơ chế dọn lock nhưng chỉ dọn trên máy Kibe, không dọn trên Admin-PC trước khi gọi runner qua SSH.

3. **Cạm bẫy báo cáo ảo (False Resolution Pitfall):**
   - Agent sửa code nhưng chưa commit vào Git hoặc chưa chạy `cron_sync_watchdog.py --force`, khiến file runtime vẫn mang logic cũ.
   - Tuyệt đối không được báo cáo "đã sửa xong" khi chưa kiểm chứng thực tế và chưa đồng bộ sang cả 2 cụm Kibe + Admin.

## 3. Quy Trình Khắc Phục Bắt Buộc
1. **Tại `run_batch_live_2fa.py` (Tầng Runner Lõi):**
   - Bọc `freeze_targets()` trong retry loop tối thiểu 5 lần với exponential backoff (2s -> 5s).
   - Tự động kiểm tra và xóa file lock `~$*.xlsx` nếu `excel.exe` không còn sống (`reap-dead-owner`).
2. **Tại `cron_night_tiktok_2fa_watchdog.py` (Tầng Điều Phối Watchdog):**
   - Trong script PowerShell remote SSH sang Admin, bắt buộc thêm lệnh kiểm tra/xóa `~$*.xlsx` mồ côi trên Admin-PC trước khi kích hoạt `run_batch_live_2fa.py`.
   - Đặt hard cooldown 45 phút khi runner gặp lỗi bootstrap (`total == 0` và `code not in (0, 4)`).
   - Sau khi sửa code watchdog, BẮT BUỘC chạy `python cron_sync_watchdog.py --force` và đồng bộ qua `sync_2fa_to_admin.py`.
