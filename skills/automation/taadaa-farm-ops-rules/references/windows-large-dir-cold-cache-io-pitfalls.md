# Windows Filesystem Cold-Cache & Large Directory I/O Gotchas

Bài học rút ra từ session chạy watchdog cron `cron_reconcile_stale_receipts.py` trên thư mục idempotency/post-attempts (~10.000 file JSON).

## 1. Hiện Tượng: Timeout 60s Do Windows Cold Disk Cache
- **Bối cảnh:** Khi một thư mục lưu trữ số lượng file lớn (ví dụ `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\` chứa >9.000 file JSON) nằm trên ổ đĩa quay (HDD) hoặc chưa được Windows File System Cache nạp (cold cache).
- **Hành vi quan sát được:**
  - `os.scandir` hoặc `glob` chỉ đọc metadata tên file: Cực kỳ nhanh (< 0.05s cho 9.300 files).
  - Mở đọc nội dung từng file (`read_text()` / `open()`): Khi cache chưa có (cold read), mỗi batch 1.000 file có thể mất 15-25 giây do I/O disk seek. Nếu đọc tuần tự 9.000 file, tổng thời gian lên tới 80-120 giây -> Lệnh chạy vượt quá timeout mặc định 60s và bị kill (exit code 124).
  - Sau khi các file đã được Windows nạp vào RAM cache (warm cache): Toàn bộ 9.000 file được đọc xong chỉ trong 1-2 giây! Lần chạy tiếp theo ngay sau đó hoàn tất trong nháy mắt.

## 2. Kỹ Thuật Tối Ưu Hóa & Tránh Timeout Cho Tooling Farm
1. **Lọc Metadata Trước Khi Đọc File (Stat Pre-filtering):**
   - Đừng mở đọc nội dung JSON của toàn bộ 10.000 file!
   - Sử dụng `entry.stat().st_mtime` từ `os.scandir` (được Windows NTFS trả về sẵn trong dirent struct, không tốn thêm I/O IOPS mở file):
     ```python
     now_ts = time.time()
     # Chỉ đọc nội dung file nếu mtime phù hợp tiêu chí (ví dụ: cũ hơn min_age hoặc nằm trong khoảng nghi ngờ)
     if (now_ts - entry.stat().st_mtime) < min_age_seconds:
         continue
     ```
   - Điều này giảm số lượng file cần `open()` từ 9.000 file xuống chỉ còn vài chục file, biến thời gian chạy từ 90s xuống < 0.1s ngay cả khi cold cache!

2. **Tăng Timeout Hoặc Warm-up Cho Các Lệnh Audit Hàng Loạt:**
   - Với các script watchdog duyệt thư mục lớn chưa được tối ưu stat-prefilter, timeout 60s có thể gây timeout giả (transient timeout) ở lần chạy đầu tiên.
   - Khi gặp timeout 60s trên script duyệt file: Kiểm tra ngay I/O cold cache trước khi kết luận script bị deadlock hay lỗi logic.

3. **Cơ Chế Binary Head/Slice Probe Để Kiểm Tra Trạng Thái Hàng Loạt:**
   - Khi cần kiểm tra nhanh hàng ngàn file JSON (như lọc các file không phải `status: completed`), thay vì `json.load()` parsing toàn bộ cấu trúc:
     ```python
     with open(entry.path, 'rb') as f:
         header = f.read(512)
     if b'"status": "completed"' not in header and b'"status":"completed"' not in header:
         # Chỉ parse chi tiết các file khả nghi
     ```
   - Đọc slice nhị phân `read(512)` nhanh hơn parse JSON đầy đủ gấp hàng chục lần và giúp loại trừ 99% file hợp lệ mà không bị vướng bottleneck CPU/parsing.

4. **Lưu Ý Coordinator Guard Khi Debug CLI:**
   - Lệnh inline `python -u -c ...` có cờ `-u` sẽ bị Coordinator Guard chặn (default-deny) do matcher kiểm tra tiền tố chính xác `python -c`. Khi chạy inline probe one-liner trên terminal, luôn dùng cú pháp chuẩn `python -c "..."` không chèn thêm cờ lạ.

5. **Chiến Lược Cấp Tốc Xử Lý Hiện Trường Khi Gặp Timeout 124 (Fast Binary Warm-up):**
   - Khi gặp timeout 60s trên lệnh cron duyệt thư mục lớn mà không được phép sửa code script:
   - Dùng lệnh probe một dòng đọc lướt nhị phân header siêu nhỏ (`f.read(128)`) để kích hoạt Windows File System Cache nạp block dữ liệu vào RAM:
     ```bash
     python -c "import os; [open(e.path, 'rb').read(128) for e in os.scandir(r'D:\path\to\dir') if e.is_file()]"
     ```
   - Quá trình này chỉ mất ~8-10s cho ~10.000 files (thay vì >80s nếu parse JSON/đọc text đầy đủ), sau đó chạy lại lệnh cron gốc sẽ pass ngay trong < 2s mà không làm thay đổi trạng thái file hay vi phạm timeout.
