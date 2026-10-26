# Case Study: Watchdog Timeout & File-Scan Bottleneck (Stale Receipts Reconcile)

## Context
Cron watchdog `cron_reconcile_stale_receipts.py` chạy với giới hạn timeout 60s để dọn dẹp các receipt kẹt trong thư mục idempotency post-attempts (`D:\CodexRuntime\tiktok-video\idempotency\post-attempts`).

## Problem
- Thư mục tích lũy hơn 9.200 file receipt JSON.
- Quá trình scan `find_stale_receipts()` mở và parse JSON tuần tự toàn bộ file (`read_text()` + `json.loads()`).
- Trên Windows NTFS, I/O đọc 9.200 file JSON tốn >60s, dẫn đến tiến trình bị timeout (exit code 124) và không bao giờ hoàn tất chu kỳ dọn dẹp.

## Fidelity & Performance Rule
- **Fast-Filter Pre-check:** Khi quét thư mục chứa hàng nghìn file để tìm bản ghi cũ (stale >= 24h), bắt buộc kiểm tra `st_mtime` (hoặc `os.scandir().stat().st_mtime`) TRƯỚC khi thực hiện đọc file disk I/O.
- Bỏ qua ngay các file có `st_mtime` mới hơn `min_age_hours` để loại bỏ 95%+ I/O disk không cần thiết.
- Đảm bảo timeout của cronjob phản ánh quy mô dữ liệu thực tế nếu số lượng file tích lũy lớn.
