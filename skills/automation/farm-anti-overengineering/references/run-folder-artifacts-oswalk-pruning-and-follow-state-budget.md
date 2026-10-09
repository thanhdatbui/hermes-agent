# Run Folder Artifacts `os.walk` Pruning & Follow State Budget Invariants

References:
- Phiên 07/09/2026: Điều tra số lượt follow trước khi nhả của 47 máy Row 1 phiên gần nhất và cập nhật phân nhóm báo cáo `feed_session_watchdog.py`.

---

## 1. BẪY `os.walk` TRONG RUN FOLDER KHÔNG PRUNE `artifacts/` (TIMEOUT 900s TRAP)

### Triệu chứng & Nguyên nhân
- Khi duyệt tìm `summary.txt`, `follow_result.json`, hoặc `upload_result.json` trong thư mục live run:
  `D:\Taadaa\runtime\kibe\live\<date>\<run_name>\<timestamp>\`
- Thư mục con `artifacts/` chứa hàng vạn file chụp màn hình (PNG), video quay màn hình, trace dumps từ 70-80 máy.
- Nếu chạy `os.walk(run_dir)` thông thường hoặc `glob.glob('.../**', recursive=True)`, Windows I/O bị nghẽn nghiêm trọng:
  + Lệnh `parse_run_all` chạy mất **343.8 giây** (> 5.7 phút).
  + Lệnh `glob.glob` đệ quy dính **Timeout 900s** (15 phút làm đơ toàn bộ phiên).

### Giải pháp bắt buộc (In-place Dir Pruning & Direct Path)
1. **Trong mọi vòng lặp `os.walk(run_dir)`:**
   BẮT BUỘC prune thư mục `artifacts` ngay tại danh sách `dirs` trước khi `os.walk` đệ quy vào trong:
   ```python
   for root, dirs, files in os.walk(run_dir):
       # Prune artifacts in-place to avoid traversing tens of thousands of screencaps/dumps
       dirs[:] = [d for d in dirs if d != "artifacts"]
       # Xử lý các file đích: summary.txt, follow_result.json, upload_result.json
   ```
2. **Khi tra cứu máy cụ thể:**
   Đi thẳng vào đường dẫn chuẩn hóa `machines/machine_<m>/follow_result.json`, CẤM TUYỆT ĐỐI dùng `glob.glob(..., recursive=True)`.

---

## 2. PHÂN BIỆT CẤU TRÚC `follow_state_*.json` VS `follow_result.json`

Khi thống kê số lượt follow trước khi máy bị nhả follow (`FOLLOW_FAILED` / `follow_failed = True`):

| Trường dữ liệu | `follow_state_<m>_row_<r>.json` (`tiktok-follow/runs/state/`) | `follow_result.json` (`live/<date>/<run>/.../machines/machine_<m>/`) |
| :--- | :--- | :--- |
| **`followed`** | **Kiểu `dict`**: Chứa toàn bộ UID đã từng follow trong **lịch sử tích lũy nhiều ngày** (100–170 keys). **CẤM** dùng `len(state['followed'])` để tính số lượt trong ngày. | **Kiểu `list`**: Danh sách UID follow được **trong chính phiên chạy đó**. |
| **`budget_used`** | **Kiểu `int`**: Số lượt follow máy đã thực hiện **trong ngày hiện tại** (`budget_date: YYYY-MM-DD`). | Có thể là `None` hoặc `int`. |
| **`follow_failed`** | `True` nếu máy bị TikTok nhả follow (tài khoản không tăng lượt follow hoặc bị hủy ngay sau vuốt). | `True` khi `status == "FOLLOW_FAILED"` và không có lỗi hệ thống khác. |

**Quy tắc:** Để lấy số lượt follow trước khi bị nhả:
- Nếu đọc từ `follow_state_*.json`: Dùng `state.get('budget_used', 0)` (kiểm tra `budget_date == today`).
- Nếu đọc từ `follow_result.json`: Dùng `len(result.get('followed', []))`. Khi có nhiều run trong phiên, merge qua `merge_follow_result` để gộp danh sách UID không trùng lặp.

---

## 3. QUY CHUẨN PHÂN NHÓM BÁO CÁO NHẢ FOLLOW (FOLLOW RELEASED BUCKETING)

Trong `feed_session_watchdog.py`, không gộp chung toàn bộ máy nhả follow thành 1 dòng đơn điệu. Bắt buộc phân thành 4 nhóm để Coordinator và user đánh giá chính xác tình trạng tài khoản và proxy:

- **Nhóm 1: Nhả liền (0 lượt)** — Vừa bấm follow anchor/target đầu tiên hoặc kiểm tra sau vuốt đã bị TikTok nhả ngay lập tức. Cần kiểm tra proxy, device fingerprint hoặc nick bị shadowban nặng.
- **Nhóm 2: 1 – 4 lượt** — Follow được vài tài khoản đầu rồi bị chặn.
- **Nhóm 3: 5 – 9 lượt** — Đạt số lượt trung bình trước khi bị nhả.
- **Nhóm 4: 10+ lượt** — Hoàn thành khối lượng đáng kể trước khi chạm ngưỡng/nhả.

**Quy tắc hiển thị Telegram:**
- Chỉ in các dòng nhóm có số máy > 0 để tiết kiệm ký tự và chống spam dòng rỗng.
- Kèm số lượt cụ thể cho từng máy ở các nhóm 2, 3, 4: `f"{m} ({cnt} lượt)"`.
