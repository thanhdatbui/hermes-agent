# Quy trình truy vết O(1) khi kênh dừng đăng video lâu ngày (Stale Channel Upload Timeline Triage)

## Bối cảnh
Khi user hỏi: *"Kênh @username sao lâu rồi không đăng video?"*, *"Lí do video kênh này cuối cùng đăng từ tận dd/mm?"*:
Không đoán mò, không quét đĩa diện rộng (`grep -r`, `find`, `os.walk`). Thực hiện đúng 5 bước định vị O(1):

---

## 5 Bước chẩn đoán chính xác

### Bước 1: Tra cứu vị trí máy và slot trong SQLite
Truy vấn bảng `account_mapping` hoặc `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db`:
```python
import sqlite3
conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
row = conn.cursor().execute("SELECT machine, row FROM account_mapping WHERE username = ?", (username,)).fetchone()
# Hoặc từ farm_account_info: (may, tik)
```
Xác định được: Máy `M`, Row `R` (tương ứng file `Tik{R}.xlsx`).

### Bước 2: Kiểm tra kho video và số video đã đăng trong workbook
Mở `D:/OneDrive/TaadaaData/kibe/Tik{R}.xlsx` (hoặc cụm admin nếu máy >= 201):
- Đọc dòng máy `M`: Folder Video, Video Đã Đăng, Render Status, Render MP4 (chuẩn 45 clip).
- Nếu thiếu video render -> Báo nguyên nhân thiếu video.
- Nếu video còn nhiều (đã đăng < Render MP4) -> Chuyển Bước 3.

### Bước 3: Tra cứu lịch sử upload thực tế qua Global Ledger (<5ms)
Đọc `C:/ProgramData/Taadaa/tiktok-upload-concurrency-v1/shift_upload_history.json`:
- Lọc theo `account == username` hoặc `(machine == M and row == R)`.
- Xác định chính xác ngày và timestamp upload thành công cuối cùng, video số mấy.

### Bước 4: Kiểm tra lịch xoay ca Farm (Row Cadence Cycle)
Farm luân phiên 8 Row (Tik1..Tik8) theo các ca sáng/trưa/tối để nuôi an toàn:
- Duyệt các ngày từ ngày đăng cuối đến hôm nay trong `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/`.
- Kiểm tra xem thư mục `row-{R}-*` có xuất hiện vào những ngày nào.
- Nếu giữa khoảng thời gian đó Row không có lịch -> Giải thích rõ lịch xoay ca (mỗi Row chỉ chạy cách 3–4 ngày).

### Bước 5: Đọc log run_manifest.json của các ca có lịch nhưng không lên video
Với các ngày Row có chạy nhưng kênh không lên clip mới, mở trực tiếp run directory:
`D:/Taadaa/runtime/kibe/live/<date>/row-{R}-<time>/<run_id>/machines/machine_{M}/<session_id>/run_manifest.json`
và `summary.txt`:
- Phân loại lỗi chuẩn:
  * `blocked-proxy-vpn`: Proxy rớt mạng lúc ca chạy.
  * `prepare-tiktok failed to focus TikTok after launch`: TikTok bị văng/treo nền trên thiết bị.
  * `hard outer watchdog deadline expired` (kèm SystemUI occlusion): Màn hình bị dialog/popup hệ thống che.
  * `organic-rest-day-upload-disabled`: Rơi vào ngày dưỡng sinh (Organic Rest 1/3).
- Kiểm tra liveness hiện tại của máy qua `python D:/Taadaa/tools/inspect_machine.py <M>` và proxy để báo cáo người dùng thời điểm ca tiếp theo sẽ khắc phục.
