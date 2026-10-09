# Quy tắc & Kỹ thuật Đối soát Following Web (feed_session_watchdog.py)

## 1. Đồng bộ file watchdog song song
Mỗi khi chỉnh sửa `feed_session_watchdog.py`, bắt buộc đồng bộ đồng thời 2 file:
- `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` (Script chạy thực tế trên máy host/cron của Hermes)
- `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py` (Script quản lý source git trong repo)

## 2. Cơ chế đối soát Following web theo `session_start_iso` (`reconcile_cluster_following`)
- **Vấn đề**: Trước đây `reconcile_cluster_following` lấy `LIMIT 2` gần nhất trong SQLite table `snapshots` của `D:/Taadaa/data/tiktok_tracker.db`. Nếu tài khoản được cào nhiều lần giữa chừng hoặc có cron cào tracker định kỳ ngoài phiên, `LIMIT 2` chỉ tính độ chênh giữa 2 lần cào gần nhất chứ không phải độ tăng thực tế kể từ đầu phiên, dẫn đến việc đối soát báo lệch số hoặc tăng 0 dù trong phiên có follow thành công.
- **Giải pháp chuẩn hóa**:
  1. Nhận tham số `session_start_iso: Optional[str] = None` từ hàm gọi (ví dụ: `f"{target_date} {win['start']}:00"`).
  2. Lấy snapshot mới nhất:
     ```sql
     SELECT following, timestamp
     FROM snapshots
     WHERE LOWER(username) = LOWER(?)
     ORDER BY timestamp DESC, id DESC
     LIMIT 1
     ```
  3. Lấy baseline snapshot chuẩn tại mốc bắt đầu phiên:
     ```sql
     SELECT following, timestamp
     FROM snapshots
     WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
     ORDER BY timestamp DESC, id DESC
     LIMIT 1
     ```
     với tham số `(u, session_start_iso)`.
  4. Nếu không tìm thấy baseline trước phiên (tài khoản mới được cào lần đầu trong phiên), fallback lấy bản ghi thứ 2 (`LIMIT 2`).
  5. Tính delta tăng thực: `delta = latest_fl - prev_fl` và đối soát với số lượt script runner báo cáo (`rep_cnt`).
