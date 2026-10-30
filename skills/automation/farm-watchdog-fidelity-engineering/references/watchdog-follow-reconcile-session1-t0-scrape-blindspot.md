# Watchdog Follow Reconcile: Pitfall T0 Missing on Shift Session 1 (Feed-only / Early Session)

## Bối cảnh sự cố
Trong báo cáo của `tiktok-follow-session-watchdog` (Ca 3 - Phiên 1/2 Tối, Run `row-0-180105`), 4 máy (M17, M24, M42, M68) có follow chéo / tự nhiên phát sinh nhưng bị watchdog gắn nhãn:
```text
- M17 [Tik 5] (@user51904226): script báo 14 (chéo 14, tự nhiên 0) | baseline cũ (2026-10-29 10:03) | UNPROVEN
```
Mặc dù thực tế trong database `snapshots`, following của nick đích và nick cày đều tăng khớp 100% (ví dụ `@user51904226` tăng từ 7 lên 21, đúng +14 lượt).

---

## Nguyên nhân gốc rễ (Root Cause)
1. **Thiết kế lệch pha giữa Runner và Watchdog:**
   - Trong kiến trúc nuôi acc theo ca, mỗi ca có 2 phiên. Ban đầu Phiên 1/2 (`session_index == 1`) được xem là "Feed only", Phiên 2/2 (`session_index == 2`) mới chạy Follow/Upload hook.
   - Do đó, watchdog ban đầu được thiết kế: Phiên 2 được buffer +30m (`buffer_reconcile_iso(session_start_iso, 30)`), trong khi Phiên 1 bị gán cứng **0 phút buffer**:
     ```python
     query_start_iso = session_start_iso if is_p1_or_unknown else buffer_reconcile_iso(session_start_iso, 30)
     ```
2. **Điểm mù cửa sổ truy vấn baseline Phiên 1 (Zero-Buffer Blindspot):**
   - Kể cả khi Runner đã cào snapshot T0 đầu ca (ví dụ lúc `18:02:03` cho ca `18:00:00`), do `query_start_iso` của Phiên 1 bị cố định ở `18:00:00`, câu lệnh SQL:
     ```sql
     WHERE LOWER(username) = LOWER(?) AND timestamp <= query_start_iso
     ```
     đã **loại bỏ thẳng tay** snapshot `18:02:03` vì `18:02:03 > 18:00:00`!
   - Watchdog buộc phải lùi về snapshot từ ca sáng (10:04:08).
   - Khoảng cách `18:00:00 - 10:04:08 = 7h56m > 4h` kích hoạt guard `is_stale_baseline = True` ➔ Xuất nhãn `UNPROVEN` dù runner đã follow thành công 100%.
3. **Cạm bẫy khi cấp Buffer cho Phiên 1 (Snapshot Collision):**
   - Nếu chỉ đơn thuần buffer Phiên 1 lên 15m mà không ràng buộc với `latest_row`, trong các ca ngắn hoặc test case mock, query baseline có thể chọn nhầm chính snapshot kết thúc phiên (latest_row), dẫn đến $\Delta_{\text{web}} = 0$.
   - BẮT BUỘC phải kèm điều kiện so sánh nghiêm ngặt: `AND timestamp < str(latest_row[1])`.

---

## Quy tắc phòng tránh & Khắc phục chuẩn (Invariant)
1. **Buffer 15 phút cho Phiên 1 + Strict Prior Condition:**
   - Sửa dòng xác định `query_start_iso` trong `feed_session_watchdog.py`:
     ```python
     query_start_iso = buffer_reconcile_iso(session_start_iso, 15 if is_p1_or_unknown else 30)
     ```
   - Thêm điều kiện SQL chặn lấy nhầm snapshot latest:
     ```sql
     SELECT following, timestamp
     FROM snapshots
     WHERE LOWER(username) = LOWER(?) AND timestamp <= ? AND timestamp < ?
     ORDER BY timestamp DESC, id DESC
     LIMIT 1
     ```
     với params `(u, query_start_iso, str(latest_row[1]))`.
2. **Bản chất "4-Way Parity" (Anti-Stale Runtime, Không phải Over-Engineering):**
   - Không phải viết code phức tạp hay over-engineering, mà là **chống chạy code cũ**: Cron Scheduler của Windows chỉ đọc `%LOCALAPPDATA%\hermes\scripts`. Nếu chỉ sửa trong Git Repo mà không sync sang `%LOCALAPPDATA%`, watchdog vẫn tiếp tục chạy code cũ bị lỗi. Sửa xong bắt buộc chạy `python cron_sync_watchdog.py --force`.
3. **Tách bạch giữa Unproven do thiếu data vs Lỗi logic runner:**
   - Khi gặp `UNPROVEN`, kiểm tra ngay timestamp của snapshot trong SQLite `snapshots` so với mốc đầu ca và các nick đích (`hang.bui813`, `yaelmssp62p`). Nếu follower nick đích tăng thật, lỗi 100% nằm ở cửa sổ query baseline của watchdog, không phải do runner hay thiết bị.
