# Directory Stat-Before-Read Pattern for High-Volume Monolith Directories

## Bối cảnh & Hiện tượng
- Trong các hệ thống chạy cron/watchdog trên Windows NTFS, các thư mục idempotency receipts, log artifacts, hoặc state tracking thường phình to lên hàng ngàn tới hàng vạn file (ví dụ: `>9,000` files).
- Khi script chạy tuần tự `Path.glob("*.json")` và gọi `json.loads(f.read_text())` cho mọi file:
  - Windows file I/O latency bị nghẽn nghiêm trọng (read latency), tổng thời gian thực thi vượt quá 60s và gây timeout (`exit_code 124`) ở cron harness.

## Nguyên Tắc Tối Ưu: Stat-Before-Read
1. **Dùng `os.scandir` thay vì `Path.glob`:**
   - `os.scandir` tận dụng metadata cache của hệ điều hành, duyệt qua 10,000 files chỉ mất ~0.02s - 0.05s.
2. **Lọc sơ bộ theo metadata `entry.stat().st_mtime` trước khi đọc nội dung:**
   - Nếu điều kiện cần của task là file cũ/stale quá `min_age` (hoặc ngược lại chỉ quan tâm file mới):
     ```python
     # Lọc sơ bộ bằng mtime để loại bỏ ngay 95%+ file không thỏa mãn mà KHÔNG tốn I/O mở file
     age_hours_mtime = (now_ts - entry.stat().st_mtime) / 3600.0
     if age_hours_mtime < min_age_hours:
         continue
     ```
3. **Chỉ parse nội dung (file read & json load) trên tập ứng viên đã qua bộ lọc:**
   - Giảm lượng I/O từ `N` (hàng vạn lượt đọc đĩa) xuống `M << N` (chỉ các file nghi vấn), giúp watchdog hoàn tất chỉ trong 1-2 giây thay vì bị timeout.
