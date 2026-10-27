# Bẫy 2-Way Sync Của cron_sync_watchdog Ghi Đè Ngược & Dirty Revert Bản Fix Git

## 1. Hiện Tượng Thực Tế
- User và agent đã fix lỗi logic (ví dụ chống spam lặp lại của watchdog) và commit lên Git repo deploy lúc 13:30.
- Tuy nhiên đến ca tối (22:31 & 22:33), Telegram tiếp tục bị bắn bản tin lỗi lặp lại liên tiếp y hệt nhau.
- Kiểm tra `git status` trong repo deploy: file script watchdog bị ở trạng thái dirty modified (`M`), và `git diff` cho thấy toàn bộ diff vừa commit bị revert ngược về code cũ!

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Kiến trúc đồng bộ 2 chiều (2-way sync) trong `cron_sync_watchdog.py`:**
   - Chiều 1: `DEPLOY_SCRIPTS` -> `KIBE_SCRIPTS` & `ONEDRIVE_SCRIPTS`.
   - Chiều 2: `KIBE_SCRIPTS` -> `DEPLOY_SCRIPTS` & `ONEDRIVE_SCRIPTS` (nhằm mục đích đồng bộ nếu có "sửa nóng" ở runtime).
2. **Bẫy mtime (Timestamp collision) & Kẹt cờ `--force`:**
   - Khi commit Git tại repo deploy lúc 13:30, file có timestamp 13:30.
   - Thư mục runtime hoặc OneDrive vì lý do đồng bộ đám mây/touch tiến trình được cập nhật timestamp lên 17:39.
   - Hàm `sync_file(src, dst, force=False)` có đoạn mã:
     ```python
     if dst_mtime > src_mtime + MTIME_TOLERANCE_S:
         return "skipped"
     ```
     Kể cả khi truyền `force=True`, điều kiện này nằm TRƯỚC khối kiểm tra `if not force: ... return "conflict"`, khiến chiều `Deploy -> Runtime` bị skip hoàn toàn.
   - Đến Chiều 2 (`Runtime -> Deploy`), vì `src_mtime (Runtime: 17:39) > dst_mtime (Deploy: 13:30)`, watchdog nhận định Runtime là bản mới hơn và **tự động copy đè file cũ từ Runtime về Git Deploy**!
3. **Hậu quả:**
   - Bản commit Git bị dirty revert ngầm trong working tree mà không ai hay biết.
   - Runtime tiếp tục chạy code cũ bị lỗi, gây tái phát sự cố dù đã fix ở session trước.

## 3. Quy Tắc & Giải Pháp Khắc Phục Bắt Buộc
1. **Khôi phục bản Git chuẩn (Single Source of Truth):**
   - Khi phát hiện watchdog bị lỗi lại dù đã fix, kiểm tra ngay `git diff` trên repo deploy.
   - Chạy `git checkout -- <file>` để discard bản đè bẩn.
2. **Vá cờ `--force` trong `cron_sync_watchdog.py`:**
   - Khi có cờ `force=True`, Deploy BẮT BUỘC có quyền lực tối cao ghi đè lên Runtime và OneDrive bất chấp `dst_mtime`:
     ```python
     if dst_mtime > src_mtime + MTIME_TOLERANCE_S and not force:
         return "skipped"
     ```
3. **Quy trình Closeout sau khi sửa Cron Watchdog:**
   - BẮT BUỘC chạy `cron_sync_watchdog.py --force` ngay sau khi sửa và kiểm tra `git status` phải sạch.
   - Sau khi sync, kiểm tra hash SHA256 giữa Deploy, Runtime và OneDrive phải khớp 100%.
