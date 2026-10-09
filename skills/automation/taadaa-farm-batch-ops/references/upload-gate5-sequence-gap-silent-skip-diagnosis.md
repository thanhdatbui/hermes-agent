# Chẩn đoán lỗi nick ngừng đăng video do đứt chuỗi số (Gate 5 Silent Safe-Skip)

## 1. Triệu chứng hiện trường
- Nick TikTok trên Phone Farm (hoặc user thắc mắc) đột nhiên ngừng đăng clip trong nhiều ngày (ví dụ > 1 tuần) dù máy vẫn hoạt động, vẫn lướt feed bình thường.
- Telegram Watchdog không hề bắn Red Alert vì không có crash hay unhandled exception.
- Số video trên profile khớp chính xác với số video ghi nhận lần upload thành công cuối cùng trong `shift_upload_history.json`.

## 2. Bản chất kỹ thuật (Root Cause)
Trong luồng upload của farm (`multi_machine_feed_session.py` -> `_run_upload_hook`):
1. **Tính toán clip kế tiếp:**
   `next_video = posted_count + 1` (lấy từ cột `Video Đã Đăng` trong file `Tik<N>.xlsx`).
2. **Kiểm tra Gate 5 (Next Video Render Preflight):**
   Đường dẫn kiểm tra: `D:\TIKTOK-videonuoinick\<Folder_Video>\<next_video>.mp4`.
3. **Cơ chế Silent Safe-Skip:**
   Nếu file không tồn tại hoặc kích thước bằng 0:
   ```python
   payload = {
       "machine": account.machine,
       "row": account.account_row_index,
       "status": "skipped",
       "reason": "video_not_rendered",  # hoặc missing_video_render
       "expected_video": str(video_file),
       "workbook": workbook_path.name,
   }
   ```
   Hệ thống coi đây là hành vi an toàn (chờ render xong mới đăng) nên **không crash, không dừng feed, không bắn alert đỏ**, dẫn đến nick bị treo đăng vô thời hạn.

4. **Nguyên nhân khuyết số trong folder clip:**
   Các đợt render cũ khi chọn ngẫu nhiên clip từ folder video gốc (ví dụ chọn 45 clip từ 102 clip gốc) đã giữ nguyên tên gốc (`source.stem.mp4`) thay vì đổi tên tuần tự `1..45.mp4` theo `start_seq`. Nếu trong mẫu ngẫu nhiên bị khuyết số (ví dụ có `1, 2, 3, 4, 6, 7...` nhưng thiếu `5.mp4`), nick sẽ đăng trơn tru đến clip 4 rồi đứng im vĩnh viễn ở clip 5.

## 3. Quy trình 4 bước điều tra nhanh O(1)
1. **Bước 1 — Xác định Máy, Row và Folder Video:**
   Mở file Tik tương ứng (`D:\OneDrive\TaadaaData\kibe\Tik<Row>.xlsx`):
   - Đọc cột `Folder Video` (ví dụ: `261`).
   - Đọc cột `Video Đã Đăng` (ví dụ: `4`).
2. **Bước 2 — Đối soát lịch sử upload:**
   Mở `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`:
   - Tìm key `<YYYY-MM-DD>_m<May>_<username>` để xác định ngày và `video_number` của lần upload thành công cuối cùng.
3. **Bước 3 — Kiểm tra file đích:**
   Kiểm tra sự tồn tại của file `(Video_Đã_Đăng + 1).mp4`:
   `ls -la "D:/TIKTOK-videonuoinick/<Folder_Video>/<Video_Đã_Đăng + 1>.mp4"`
   Nếu báo `No such file or directory`, kiểm tra toàn bộ danh sách file trong folder:
   `ls "D:/TIKTOK-videonuoinick/<Folder_Video>" | sort -V`
   Xác định các lỗ hổng số (gaps) trong chuỗi.
4. **Bước 4 — Xử lý phục hồi:**
   - **Cách 1 (Tức thời cho 1 clip):** Lấy clip gốc tương ứng từ `D:\video goc\<ID_Goc>\<Next_Num>.mp4` render nhanh vào folder, hoặc đổi tên clip tiếp theo có sẵn thành `<Next_Num>.mp4`.
   - **Cách 2 (Toàn diện cho cả folder):** Dùng script đổi tên toàn bộ các clip còn lại trong folder thành chuỗi số thứ tự liên tục bắt đầu từ `Next_Num.mp4` (tuân thủ nguyên tắc `start_seq = Video_Đã_Đăng + 1`), tránh để sót các lỗ hổng tiếp theo.
