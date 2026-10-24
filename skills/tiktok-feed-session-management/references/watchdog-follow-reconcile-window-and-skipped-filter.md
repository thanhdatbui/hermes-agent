# Watchdog Follow Reconcile Window Buffer & Skipped Machine Filtering

## 1. Bản chất Lỗi Lệch Snapshot Web (Time Window Mismatch)
### Hiện tượng
Script báo có lượt follow chéo/tự nhiên (ví dụ 8 lượt), nhưng đối soát TikTok Web báo 0 lượt (lệch âm) dù tài khoản thực tế trên web đã tăng following.

### Nguyên nhân
- Ca nuôi kết thúc tại giờ chẵn (ví dụ: Ca 3 Phiên 1 kết thúc lúc 20:00).
- Buffer đối soát mặc định chỉ có 10 phút (`query_end_iso = session_end_iso + 10m` -> 20:10).
- Tiến trình cào profile web (`tiktok_account_tracker.py`) mất từ 5-15 phút để hoàn tất và lưu vào SQLite lúc 20:15 - 20:21.
- Mệnh đề SQL `WHERE timestamp <= query_end_iso` loại bỏ toàn bộ snapshot vừa cào và fallback về snapshot cũ lúc sáng (07:03).
- Cả mốc baseline đầu ca và mốc latest cuối ca đều trỏ vào cùng snapshot cũ -> Delta web tính ra bằng 0.

### Giải pháp Chuẩn hóa
- Nới `buffer_reconcile_iso(..., minutes=30)` cho cả `query_start_iso` (phiên 2+) và `query_end_iso`.
- Đảm bảo cửa sổ truy vấn bao phủ được toàn bộ thời gian cào sau khi kết thúc ca.

---

## 2. Lọc Máy Skipped Chống False Alarm Thiếu Username
### Hiện tượng
Farm Admin (hoặc cụm máy nghỉ dưỡng sinh / dưới 6 video) báo:
`+ Đối soát TikTok Web: Không tìm thấy username trong workbook cho N máy follow`
dù các máy này không hề phát sinh hành động follow.

### Nguyên nhân
- `target_machines` gom tất cả `all_follows.keys()`.
- Các máy có status `skipped` (0 follow, không lỗi) bị `continue` bỏ qua, không nạp vào map `m_to_user`.
- Kiểm tra `if not m_to_user and target_machines:` ngộ nhận toàn bộ các máy trong `target_machines` là máy đi follow bị thiếu username trong Excel.

### Giải pháp Chuẩn hóa
- Dùng `reconcile_targets = []` chỉ ghi nhận máy thực sự phát sinh follow (`cnt > 0` hoặc có lỗi/timeout `failed / is_timeout_or_err`).
- Chỉ kích hoạt cảnh báo thiếu username khi `reconcile_targets` có phần tử mà `m_to_user` rỗng.

---

## 3. Kỷ luật Architecture Gate trên Monolith Watchdog
- `feed_session_watchdog.py` bị ràng buộc ngân sách cứng bởi `test_watchdog_architecture_gate.py` (`<= 1450 dòng`).
- Mọi chỉnh sửa L2/Worker trên file này bắt buộc kiểm tra `wc -l` và chạy `pytest tests/test_watchdog_architecture_gate.py` trước khi commit.
- Hậu kiểm Closeout Gate: Bắt buộc chạy `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output` đạt điểm $\ge 85$ (APPROVED).
