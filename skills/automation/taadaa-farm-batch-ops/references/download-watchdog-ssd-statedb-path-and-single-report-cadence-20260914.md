# Triage & Bài Học Vận Hành: Watchdog Download Ưu Tiên SSD state.db & Kỷ Luật Báo Cáo Avatar Single-Shift (2026-09-14)

## 1. Sự Cố Số Liệu Watchdog Video Gốc Bị Đứng Im ("Có tăng đc video gốc đéo nào đâu????")

### Hiện tượng:
- Cronjob `farm-render-download-watchdog` (báo cáo định kỳ mỗi 1h về Farm Alert) liên tục báo số liệu video gốc Kibe đứng im ở mốc cũ:
  `Tổng folder nguồn: 512 | Đạt ≥ 30 video: 503 | Đạt ≥ 45 video: 398 | Tổng video mp4 gốc: 27,113 video`
- Trong khi đó, tiến trình downloader (`download_by_niche.py`, PID 15808, 20 workers, 67 proxy) đã chạy suốt đêm và trạng thái vẫn hiện `🟢 Đang chạy`.

### Nguyên nhân cốt lõi (Root Cause):
1. **Lệch đường dẫn lưu trữ giữa SSD Runtime và HDD Storage:**
   - Để giải phóng nghẽn I/O ổ đĩa cơ HDD (tránh bị timeout 180s khi SQLite lock/query), tiến trình download chạy với cờ `--state-db "C:/CodexRuntime/tiktok-video/state.db"` trên ổ SSD NVMe.
   - Tuy nhiên, script watchdog dùng chung `farm_render_download_watchdog.py` trong hàm `detect_host()` lại hardcode đường dẫn tới ổ đĩa cơ cũ: `"state_db": r"D:\CodexRuntime\tiktok-video\state.db"`.
   - Kết quả: Downloader liên tục ghi nhận video mới vào SSD C:, trong khi Watchdog lại truy vấn file SQLite đóng băng trên ổ D:. Số liệu thực tế trên SSD đã đạt **583 folder nguồn, 523 folder ≥ 30, 412 folder ≥ 45, 28,235 clip** (tăng thêm +71 folder và +1,122 clip mới) nhưng người vận hành nhìn thấy báo cáo tưởng tool bị treo.
2. **Bẫy ký tự thoát chuỗi `\t` (Tab Escape) trên Windows:**
   - Khi định nghĩa đường dẫn trong Python dạng `r"C:\CodexRuntime\tiktok-video\..."`, nếu vô tình dùng chuỗi thường hoặc nối chuỗi không cẩn thận, đoạn `\t` trong `\tiktok-video` sẽ bị chuyển thành ký tự Tab `\t` (`0x09`), dẫn đến lỗi `FileNotFoundError` hoặc truy vấn sai file.

### Giải pháp chuẩn hóa:
- Trong `farm_render_download_watchdog.py`, đường dẫn `state_db` cho Kibe BẮT BUỘC dùng cơ chế ưu tiên kiểm tra SSD trước, fallback HDD sau, và luôn dùng forward-slash `/`:
  ```python
  "state_db": (
      r"C:/CodexRuntime/tiktok-video/state.db"
      if os.path.exists(r"C:/CodexRuntime/tiktok-video/state.db")
      else r"D:/CodexRuntime/tiktok-video/state.db"
  ),
  ```
- Định kỳ sync ngược `state.db` từ SSD C: sang HDD D: sau khi download hoàn tất để làm bản backup lưu trữ.

---

## 2. Kỷ Luật Báo Cáo Avatar Watchdog: "Chạy Xong Hết Rồi Mới Được Báo" (User chốt 13/09/2026)

### Phản ánh từ người vận hành:
- Khi batch up avatar Row 5 chạy đợt 1 (40 phút) fail nhiều máy do mạng, watchdog bắn báo cáo kết quả đợt 1. Sau đó watchdog tự động cuốn chiếu kích hoạt đợt 2 chạy tiếp 40 phút rồi lại bắn báo cáo đợt 2.
- Người vận hành bức xúc: *"là sao chạy xong ms báo 1 lần chứ 40ph báo tiếp v... YÊU CẦU CHẠY XONG HẾT R MS ĐC BÁO, MÀ WORKER NÓ ĐNAG ĐỂ BN MÀ CHẠY CHẬM V"*.

### Quy chuẩn cấu hình & Nhịp báo cáo (Report Cadence):
1. **Khóa cứng Concurrency: 30 workers song song (`-MaxParallel 30`):**
   - Không để 20 workers vì quá chậm (phải chia 4 hàng đợi mất 40 phút/batch).
   - Không để 40 workers trên background watchdog để tránh dồn dập socket ADB khi farm vừa hết ca lướt feed.
   - Mức **30 workers** là điểm cân bằng vàng: farm 60–80 máy chỉ cần 2 lượt chạy, rút ngắn thời gian batch xuống còn ~15–20 phút.
2. **Kỷ luật Silent Rolling Batch (Im lặng tuyệt đối khi cuốn chiếu):**
   - Khi mỗi đợt chạy con kết thúc, watchdog chỉ âm thầm cập nhật state nội bộ (`state["running_batch"] = None`).
   - TUYỆT ĐỐI CẤM gửi tin nhắn Telegram sau từng đợt chạy lẻ tẻ.
3. **Cơ chế Single-Shift Final Summary (Chỉ báo DUY NHẤT 1 lần):**
   - Chỉ phát đúng 1 tin nhắn Farm Alert tổng kết duy nhất trong 2 kịch bản:
     + **Kịch bản A (Xong 100%):** Toàn bộ các Tik (`5, 6, 7, 8, 3, 4`) đều có 0 máy tồn (`get_unuploaded_machines(tik) == []`).
     + **Kịch bản B (Hết khung giờ ca tối):** Sau 23:30 (hết ca tối), watchdog tự động đóng sổ, bắn đúng 1 tin tổng kết toàn ca liệt kê số máy thành công và số máy còn tồn theo từng Tik, sau đó ghi nhận `last_reported_date` để khóa không gửi thêm tin nhắn nào trong đêm.
