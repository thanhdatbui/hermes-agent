# Quy tắc Đối Soát Follow và Kỷ Luật Bộ Đếm Watchdog TikTok Nuôi Acc

## 1. Cơ Chế Chống Cộng Dồn Lặp x3 (Idempotent Watchdog Staging)
- **Bối cảnh lỗi:** Watchdog chạy cron định kỳ 5 phút/lần. Khi một phiên kết thúc ở cụm Kibe nhưng chưa gửi báo cáo ngay (do còn đợi cụm Admin hoàn tất), Watchdog quét lại phiên đó nhiều lần.
- **Lỗ hổng cũ:** Sử dụng câu lệnh SQL cộng dồn mù quáng:
  ```sql
  ON CONFLICT(target_date, username) DO UPDATE SET
      internal_follows = daily_account_actions.internal_follows + excluded.internal_follows
  ```
  Khiến mỗi tick 5 phút lại cộng thêm một lần, nhân số follow của phiên lên x2, x3 (ví dụ 10 lượt bị thành 30 lượt).
- **Chuẩn hóa kiến trúc (Idempotent Staging):**
  1. Tạo bảng trung gian theo phiên:
     ```sql
     CREATE TABLE IF NOT EXISTS session_account_actions (
         session_key TEXT,
         cluster TEXT,
         target_date TEXT,
         username TEXT,
         may INTEGER,
         internal_follows INTEGER DEFAULT 0,
         updated_at TEXT,
         PRIMARY KEY (session_key, cluster, username)
     );
     ```
  2. Mỗi lần đối soát phiên, chỉ ghi đè đúng `session_key` của phiên đó:
     ```sql
     INSERT INTO session_account_actions ...
     ON CONFLICT(session_key, cluster, username) DO UPDATE SET
         internal_follows = excluded.internal_follows,
         updated_at = excluded.updated_at
     ```
  3. Bảng `daily_account_actions` tổng hợp bằng `SUM(internal_follows)` từ các `session_key` riêng biệt của ngày hôm đó:
     ```sql
     INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
     SELECT target_date, username, MAX(may), SUM(internal_follows), MAX(updated_at)
     FROM session_account_actions
     WHERE target_date = ?
     GROUP BY target_date, username
     ON CONFLICT(target_date, username) DO UPDATE SET
         internal_follows = excluded.internal_follows,
         may = excluded.may,
         updated_at = excluded.updated_at
     ```

## 2. Quy Tắc Bộ Đếm Trừ Nhả & Follow Tự Nhiên (User Invariant)
- **Nguyên tắc căn bản:**
  - Bộ đếm trừ nhả là do chính script/device bắt tại hiện trường (`follow_failed`, `verify_follow`), KHÔNG được lấy số cào từ DB đè ngược lại làm mất tính độc lập của đối soát.
  - Khi follow chéo lượt đầu tiên = 0 (`cnt == 0` khi dính `follow_failed`): TikTok chưa nhận follow nào -> bỏ toàn bộ follow tự nhiên và chéo (`reported = 0`), khấu trừ tự nhiên khỏi tổng phiên để triệt tiêu delta âm.
  - Khi follow chéo lượt đầu tiên đã thành công (`cnt > 0`): Nick đã được server nhận các follow trước đó -> BẮT BUỘC tính đủ toàn bộ follow tự nhiên thành công (`natural_cnt`) + các lượt chéo đã bấm thành công cho tới thời điểm bị ngắt (`reported = cnt + natural_cnt`).
  - Khi nick dính `FOLLOW_FAILED` sau $N > 0$ lượt: Máy thuộc nhóm `fl_released` nhưng vẫn có `followed_count > 0` -> `target_machines` BẮT BUỘC phải bao gồm các máy này để không bỏ sót $N$ lượt đã bấm.

## 3. Đồng Bộ Telegram Report ↔ SQLite Database Dashboard
- Trong `feed_session_watchdog.py` (`reconcile_cluster_following`):
  - Biến `m_to_reported` mang giá trị tổng follow hợp lệ (chéo + tự nhiên).
  - Khi ghi vào `session_account_actions` và `daily_account_actions`, BẮT BUỘC dùng `m_to_reported.get(str(m_num), 0)` thay vì chỉ lấy `m_to_cross`.
  - Cột `🔗 Nội bộ` trên Dashboard đọc từ `daily_account_actions`, nhờ đó số liệu trên Dashboard sẽ khớp 100% với Web tăng thật và tin nhắn Telegram.
