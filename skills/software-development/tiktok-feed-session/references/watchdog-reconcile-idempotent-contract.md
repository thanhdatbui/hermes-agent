# Watchdog Reconcile Idempotent Contract (Anti Duplication x3)

## Vấn đề gốc
Trong `feed_session_watchdog.py`, hàm `reconcile_cluster_following` ghi nhận số follow chéo/nội bộ (`internal_follows`) vào bảng `daily_account_actions` trong SQLite `tiktok_tracker.db`.
Nếu watchdog chạy đối soát nhiều lần trong cùng một phiên (do loop định kỳ, retry, hoặc nhiều cửa sổ check), câu lệnh cộng dồn trực tiếp:
```sql
ON CONFLICT(target_date, username) DO UPDATE SET
    internal_follows = daily_account_actions.internal_follows + excluded.internal_follows
```
sẽ gây lỗi cộng dồn lặp nhiều lần (x2, x3, xN) cho cùng một tài khoản.

## Giải pháp: Staging Table theo Session Key
Sử dụng 2 tầng lưu trữ:
1. **Staging Table (`session_account_actions`)**:
   - Khóa chính: `PRIMARY KEY (session_key, cluster, username)`.
   - Mỗi lần chạy đối soát trong session, cập nhật giá trị tuyệt đối của session đó (`ON CONFLICT(...) DO UPDATE SET internal_follows = excluded.internal_follows`).
   - Ghi nhận `session_key` được truyền từ vòng lặp watchdog (ví dụ: `f"{target_date}_{win['start']}"`).
2. **Aggregated Table (`daily_account_actions`)**:
   - Tính tổng từ staging theo ngày:
     ```sql
     INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
     SELECT target_date, username, may, SUM(internal_follows), MAX(updated_at)
     FROM session_account_actions
     WHERE target_date = ?
     GROUP BY target_date, username, may
     ON CONFLICT(target_date, username) DO UPDATE SET
         internal_follows = excluded.internal_follows,
         updated_at = excluded.updated_at
     ```
   - Nhờ cơ chế này, watchdog chạy lại bao nhiêu lần trong cùng session thì giá trị `internal_follows` trong `daily_account_actions` vẫn bảo đảm tính idempotent 100%.

## Quy tắc đếm lượt bấm thành công trước khi nhả & Đồng bộ DB
1. **Bảo toàn lượt bấm trước khi bị nhả (`cnt > 0`)**:
   - Trong `reconcile_cluster_following`, `target_machines` BẮT BUỘC bao gồm cả các máy có `len(followed) > 0` trong `all_follows` (không chỉ lọc cứng `fl_success`), vì máy dính `follow_failed = True` sẽ bị classify thành `fl_released`.
   - Nếu `cnt > 0`: Máy đã bấm thành công $N$ lượt trước khi bị nhả $\rightarrow$ BẮT BUỘC tính đủ $N$ lượt chéo + follow tự nhiên hợp lệ (`m_to_reported = cnt + natural_cnt`).
   - Chỉ khi `cnt == 0` (lượt đầu tiên thất bại ngay): Coi như bị drop hoàn toàn, `m_to_reported = 0`.
2. **Đồng bộ giá trị ghi vào DB Staging (`session_account_actions`)**:
   - Khi ghi vào DB cho Dashboard đọc, BẮT BUỘC lấy `c_cnt = 0 if is_failed else m_to_reported.get(str(m_num), 0)`.
   - CẤM dùng `m_to_cross` vì sẽ làm mất các lượt follow tự nhiên hợp lệ đã tính trong phiên, gây desync giữa báo cáo Telegram và cột "🔗 Nội bộ" trên Dashboard.

## Đồng bộ 3 file watchdog
Khi chỉnh sửa `feed_session_watchdog.py`, bắt buộc đồng bộ đầy đủ các bản sao sau:
1. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` (Repo script)
2. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` (Hermes local active runner)
3. `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py` (Cron backup runner)
4. Kiểm chứng hồi quy bằng `pytest D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_session_watchdog.py`.
