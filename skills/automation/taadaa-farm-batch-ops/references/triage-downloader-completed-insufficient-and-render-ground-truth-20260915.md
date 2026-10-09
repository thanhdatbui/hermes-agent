# Triage Hiện Tượng Downloader Hoàn Tất Quét Đợt Thiếu Nguồn & Đối Soát Ground Truth Render

## 1. Bối Cảnh Sự Cố (15/09/2026)
- Người vận hành thắc mắc bức xúc: *"Clgt nãy h k render k down đc thêm gì cả"*.
- Cần đối soát O(1) kiểm tra ground truth cả 2 mảng: Download video gốc và Render video nuôi nick, phân biệt rạch ròi giữa:
  1. **Render vẫn đang chạy hay bị crash/treo?**
  2. **Download tại sao dừng, đã tải được gì và tại sao không tải tiếp?**

## 2. Quy Trình Điều Tra O(1) Nhanh Chóng & Chuẩn Xác

### A. Điều Tra Render (Tiktok-video)
1. **Kiểm tra tiến trình:**
   - Quét tiến trình ffmpeg và python launcher:
     ```powershell
     Get-Process | Where-Object { $_.ProcessName -match 'ffmpeg|python' } | Select-Object Id, ProcessName, CPU, WorkingSet64
     Get-CimInstance Win32_Process -Filter "CommandLine like '%random_batch_render.py%' or CommandLine like '%run_kibe_slot7_slot8_render.ps1%'" | Select-Object ProcessId, CommandLine
     ```
   - **Xác minh CPU ticking:** CPU của ffmpeg tăng liên tục (ví dụ 2929s -> 3273s -> 3797s) khẳng định ffmpeg đang encode thật, không bị deadlock.
2. **Kiểm tra file output tăng trưởng:**
   - Xem thư mục output đang render (ví dụ `D:\TIKTOK-videonuoinick\<folder>`):
     ```powershell
     Get-ChildItem 'D:\TIKTOK-videonuoinick\<folder>' | Sort-Object LastWriteTime -Descending | Select-Object -First 5
     ```
   - File có kích thước 0 byte là file ffmpeg đang mở ghi stream; các file hoàn thành có kích thước ~40-80MB với timestamp nhảy cách nhau 10-15 phút/clip.
   - Khi folder chạm 30/45 clip, render tự động chuyển sang folder kế tiếp.

### B. Điều Tra Download (download_by_niche.py & state.db)
1. **Truy vấn O(1) trực tiếp từ SQLite SSD (`C:/CodexRuntime/tiktok-video/state.db`):**
   - **CẤM TUYỆT ĐỐI** dùng `Get-ChildItem -Recurse` quét đĩa HDD `D:\video goc` vì sẽ bị timeout 180s.
   - Đọc trạng thái tổng quát:
     ```python
     import sqlite3
     conn = sqlite3.connect('C:/CodexRuntime/tiktok-video/state.db')
     c = conn.cursor()
     # Thống kê folder hoàn tất và tồn đọng
     c.execute('SELECT status, count(*) FROM folders GROUP BY status')
     print('Folder status:', c.fetchall())
     # Kiểm tra các folder vừa hoàn thành hôm nay
     c.execute('SELECT folder_num, niche, video_count, completed_at FROM folders WHERE completed_at >= date("now") ORDER BY completed_at DESC')
     print('Completed today:', c.fetchall())
     ```
2. **Nhận diện nguyên nhân Downloader dừng:**
   - Nếu tiến trình `download_by_niche.py` không còn trong danh sách tiến trình:
     - Kiểm tra trạng thái folders từ `start-folder` đến `total-folders`: Nếu các folder còn lại chuyển sang `insufficient_pool`, nghĩa là downloader đã duyệt qua hết toàn bộ nguồn trong `sources.qualified30.json` và không tìm thấy kênh nào đủ $\ge 30$ video cho các niche đó (niche cạn nguồn).
     - Downloader tự động thoát sạch sẽ (Clean Exit) với cờ `--continue-on-insufficient`.
   - **Giải phóng Stale Reservation:**
     - Nếu downloader bị tắt hoặc kết thúc mà để lại folder ở trạng thái `reserved` (nhưng không có thread tải nào active):
       ```python
       c.execute('UPDATE folders SET status = "insufficient_pool" WHERE status = "reserved"')
       conn.commit()
       ```
3. **Kết luận và hướng xử lý tiếp theo:**
   - Để tiếp tục phủ kín các folder bị `insufficient_pool` (ví dụ 98 folder từ 600..640), bắt buộc phải chạy mở rộng `source_pool_builder --auto-discover` để cào thêm kênh YouTube mới cho các niche bị thiếu, sau đó chạy `--qualify-videos` rồi mới re-run downloader.
