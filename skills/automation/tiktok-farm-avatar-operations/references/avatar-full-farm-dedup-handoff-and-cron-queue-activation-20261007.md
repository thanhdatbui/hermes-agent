# Avatar Full-Farm Dedup Handoff and Cron Queue Activation (07/10/2026)

## 1. Bối Cảnh & Các Tín Hiệu Chỉ Đạo Của Operator
Trong các đợt rà soát avatar quy mô lớn trên toàn farm (640 folders Kibe + Admin), Operator thường đưa ra 4 câu hỏi định hướng theo trình tự:
1. **"Đkm còn folder nào nhầm ava nữa k"**: Yêu cầu kiểm toán toàn diện toàn bộ kho video trên ổ đĩa và database hàng đợi, tuyệt đối không được dùng danh sách hardcode cũ.
2. **"T cho session khác xử lý vụ ava rồi kiểm tra h ổn chưa"**: Session khác đang/đã chạy song song, yêu cầu kiểm toán chéo (cross-session audit) bóc tách tiến độ đã hoàn tất vs khối lượng còn sót.
3. **"Session kia dừng r. H m quét nốt hay sao" / "Làm đi"**: Lệnh tiếp quản dứt điểm (takeover handoff) khi session trước bị ngắt/dừng ngang.
4. **"Sửa lại hàng đợi để các nick chạy khi cron gọi chưa"**: Yêu cầu kiểm chứng dứt khoát trạng thái hàng đợi `avatar_replace_queue` và sự sống của tiến trình cron watchdog.

---

## 2. Chiến Lược 2-Pass Sinh Avatar Độc Bản Toàn Farm (Zero-Duplicate)

### Pass 1: Parallel Worker Pool (8 Workers)
- Quét toàn bộ các folder số trong `D:\video goc` gom theo MD5 hash để tìm các nhóm trùng lặp (`len(folders) > 1`).
- Bỏ qua các folder rỗng video (`NO_VIDEOS`) sang danh sách cào nguồn độc lập.
- Chạy song song 8 workers gọi `_make_avatar.py` có timeout 180s để tận dụng Haar Cascade và YOLO bắt đúng chủ thể.

### Pass 2: Fast FFmpeg Targeted Pass (Xử lý Timeout & Short Video)
- Các folder phức tạp có nhiều clip nặng thường làm `_make_avatar.py` bị timeout (>180s) trên Coordinator.
- Với các folder này, chuyển sang trích xuất tức thì (<1s) bằng FFmpeg từ `1.mp4`:
  ```bash
  ffmpeg -hide_banner -loglevel error -y -ss 00:00:03.500 -i "1.mp4" -vf "crop='min(iw,ih)':'min(iw,ih)',scale=512:512" -vframes 1 -q:v 2 "avatar.jpg"
  ```
- **BẪY CLIP NGẮN (DURATION < 3.5s — CRITICAL PITFALL):**
  * Nếu video `1.mp4` có thời lượng ngắn hơn 3.5s (ví dụ folder 262 chỉ dài 2.66s), lệnh seek `-ss 00:00:03.500` sẽ vượt quá EOF, dẫn đến FFmpeg sinh frame rỗng hoặc giữ nguyên file avatar cũ làm hash tiếp tục trùng lặp với folder gốc!
  * **Giải pháp:** Luôn kiểm tra thời lượng bằng `ffprobe` hoặc fallback seek ở timestamp an toàn (`00:00:01.000`) khi gặp clip ngắn.

---

## 3. Đồng Bộ 2 Đầu Kho & Hạ Tầng Admin Remote
- Khi file `D:\video goc\<folder>\avatar.jpg` được sinh mới, BẮT BUỘC copy 1:1 sang:
  `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`
- Kiểm toán lại MD5 trên cả 2 thư mục: Bắt buộc đạt `0 duplicate groups` (100% 640 folders độc bản).
- Đồng bộ database tracker sang máy Admin Remote để watchdog bên đó có cùng hàng đợi:
  ```bash
  scp D:/Taadaa/data/tiktok_tracker.db admin-farm:D:/Taadaa/data/tiktok_tracker.db
  cp D:/Taadaa/data/tiktok_tracker.db D:/OneDrive/TaadaaData/tiktok_tracker.db
  ```

---

## 4. Quy Trình Kiểm Chứng Hàng Đợi & Cron Watchdog ("Sửa lại hàng đợi chưa")
Khi Operator hỏi *"Sửa lại hàng đợi để các nick chạy khi cron gọi chưa"*, Coordinator BẮT BUỘC kiểm tra và báo cáo 4 điểm thực tế:

1. **Kiểm tra trạng thái SQLite:**
   ```python
   import sqlite3
   conn = sqlite3.connect(r'D:\Taadaa\data\tiktok_tracker.db')
   c = conn.cursor()
   # Reset PENDING cho các folder vừa sửa
   c.execute("UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE folder_video = ? OR video_goc = ?", (folder, folder))
   # Thống kê tổng quan
   c.execute("SELECT host_id, status, count(*) FROM avatar_replace_queue GROUP BY host_id, status")
   c.execute("SELECT tik, host_id, count(*) FROM avatar_replace_queue WHERE status = 'PENDING' GROUP BY tik, host_id ORDER BY tik")
   ```
2. **Kiểm tra sự sống của tiến trình Cron Watchdog (Live Process):**
   - Không đoán mò hay chỉ xem jobs.json.
   - Quét tìm tiến trình PowerShell đang chạy script avatar:
     ```powershell
     Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*run_tiktok_upload_avatar.ps1*" } | Select-Object ProcessId, CommandLine
     ```
3. **Báo cáo bằng chứng thực tế:**
   - Số lượng tài khoản `PENDING` theo từng cụm (Kibe vs Admin) và từng Slot Tik (`Tik 1..8`).
   - PID của tiến trình batch đang chạy, số máy đang được bốc (ví dụ: đang bốc 72 máy của dàn Tik 3 Admin).
   - Khẳng định khi cron bốc máy ra chạy thì 100% file ảnh lấy từ đĩa đều là ảnh độc bản mới nhất.
