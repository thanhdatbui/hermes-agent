# Case Study: Watchdog Timeout & File-Scan Bottleneck (Stale Receipts Reconcile)

## Context
Cron watchdog `cron_reconcile_stale_receipts.py` chạy với giới hạn timeout 60s (wrapper 120s) để dọn dẹp các receipt kẹt trong thư mục idempotency post-attempts (`D:\CodexRuntime\tiktok-video\idempotency\post-attempts`).

## Problem
- Thư mục tích lũy hơn 9.600 file receipt JSON.
- Quá trình scan `find_stale_receipts()` mở và parse JSON tuần tự toàn bộ file (`read_text()` + `json.loads()`).
- Trên Windows NTFS, I/O đọc 9.600 file JSON tốn >60s (hoặc >120s khi ổ đĩa đang bận render/download), dẫn đến tiến trình bị timeout (exit code 124 / `subprocess.TimeoutExpired`) và không bao giờ hoàn tất chu kỳ dọn dẹp.
- **Bẫy Cold-Cache vs Warm-Cache (Manual Re-run Illusion):** Khi cron chạy tự động sau thời gian dài không truy cập (hoặc sau khi hệ thống chạy render/batch I/O nặng), file cache trên RAM bị xả (cold cache). Việc đọc tuần tự 9.000+ files mất 65-125s -> timeout. Tuy nhiên khi kỹ sư / agent chạy lại thủ công ngay sau đó, dữ liệu đã nằm trên Windows File Cache (warm cache) nên chạy chỉ mất 1-3s, dễ gây hiểu lầm là "lỗi mạng hoặc transient ảo" thay vì nhận diện đúng gốc rễ bottleneck I/O.
- **Bẫy Đề Xuất Di Dời/Lưu Trữ File Không Thuộc Quyền (Scope Coupling Trap):** Khi thấy thư mục có 9.600+ file, agent nảy sinh ý định "dọn dẹp di dời toàn bộ file completed sang `archived_completed/`". Đây là bẫy nguy hiểm: thư mục `post-attempts/` được dùng trực tiếp bởi runtime chính (`state_machine.py`) qua các hàm `_find_completed_post_receipts_for_machine` và `_advance_video_cursor_past_completed_receipts` để chống đăng trùng video. Nếu dọn mù quáng sang thư mục khác, runtime chính sẽ mất ledger chống trùng và đăng lặp video!

## Fidelity & Performance Rule
- **Fast-Filter Pre-check:** Khi quét thư mục chứa hàng nghìn file để tìm bản ghi cũ (stale >= 24h), bắt buộc kiểm tra `st_mtime` (hoặc `os.scandir().stat().st_mtime`) TRƯỚC khi thực hiện đọc file disk I/O.
- Bỏ qua ngay các file có `st_mtime` mới hơn `min_age_hours` để loại bỏ 95%+ I/O disk không cần thiết.
- **Không di dời / can thiệp file runtime khi chưa kiểm tra caller coupling:** Luôn kiểm tra `git grep` hoặc tìm kiếm caller trên toàn repo nghiệp vụ (`Tiktok-video`, `automation-core`) trước khi đề xuất archive/move file dùng chung.
- Đảm bảo timeout của cronjob phản ánh quy mô dữ liệu thực tế nếu số lượng file tích lũy lớn.
