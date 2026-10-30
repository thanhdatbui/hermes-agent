# Pitfall & Invariant: Watchdog Session 1 Zero-Buffer T0 Exclusion Trap

## 1. Hiện Tượng Thực Tế
Trong báo cáo định kỳ của `tiktok-follow-session-watchdog`:
```text
  + Đối soát TikTok Web (Script báo 0 lượt follow):
    - M17 [Tik 6] (@cout8792): script báo 2 (chéo 2, tự nhiên 0) | baseline cũ (2026-10-30 10:04) | UNPROVEN
```
Mặc dù runner đã được trang bị cơ chế cào T0 đầu phiên (`_scrape_pre_session_following`), và trong SQLite DB `tiktok_tracker.db` thực tế đã có snapshot T0 tươi mới được ghi nhận ngay đầu ca (lúc `18:02:03`), nhưng watchdog vẫn bỏ qua và rơi ngược về snapshot lúc `10:04:08` sáng (cũ > 7h) dẫn đến dán nhãn `UNPROVEN`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

### Bẫy Zero-Buffer ở Phiên 1 (`is_p1_or_unknown`)
Trong `feed_session_watchdog.py`:
```python
is_p1_or_unknown = is_session_key_p1_or_unknown(session_key)
query_start_iso = session_start_iso if is_p1_or_unknown else buffer_reconcile_iso(session_start_iso, 30)
```
- Đối với Phiên 2 (`is_p1_or_unknown == False`), watchdog cộng buffer 30 phút (`buffer_reconcile_iso(session_start_iso, 30)`).
- Đối với Phiên 1 (`is_p1_or_unknown == True`), watchdog gán cứng `query_start_iso = session_start_iso` (ví dụ `18:00:00`, 0 buffer).

### Lệch Pha Thời Gian Với SQL Query:
1. Cron kích hoạt runner lúc `18:00` hoặc `18:01:05`.
2. Runner spawn chạy `_scrape_pre_session_following` cào 80 tài khoản bằng multi-workers qua proxy, mất khoảng 60–120s. Snapshot T0 được ghi vào SQLite DB lúc `18:02:03`.
3. Khi watchdog truy vấn baseline snapshot:
   ```sql
   SELECT following, timestamp
   FROM snapshots
   WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
   ORDER BY timestamp DESC, id DESC LIMIT 1
   ```
   với tham số `query_start_iso = "2026-10-30 18:00:00"`.
4. Do `"18:02:03" > "18:00:00"`, snapshot T0 tươi mới **BỊ SQL LOẠI BỎ HOÀN TOÀN**!
5. SQL bắt buộc phải lùi về snapshot gần nhất trước đó: snapshot ca sáng `10:04:08`.
6. Guard `is_stale_baseline`: `(s_dt - b_dt).total_seconds() > 4 * 3600` phát hiện khoảng cách 7h56m > 4h, đánh dấu baseline cũ và dán nhãn `UNPROVEN`.

---

## 3. Quy Tắc & Cơ Chế Khắc Phục Chuẩn (Remediation Invariants)

1. **Bắt Buộc Cấp Buffer Dương Cho Cả Phiên 1:**
   - Phiên 1 bắt buộc có buffer tối thiểu 15 phút:
     ```python
     query_start_iso = buffer_reconcile_iso(session_start_iso, 15 if is_p1_or_unknown else 30)
     ```
   - Điều này đảm bảo toàn bộ snapshot T0 được cào trong 15 phút đầu ca (thường rơi vào phút 1–5) luôn nằm trong khoảng `timestamp <= query_start_iso` và được chọn làm baseline hợp lệ.

2. **Kỹ Thuật Target Account Follower Audit (Đối Soát Nick Đích):**
   - Khi counter `following` trên trang công khai của nick cày chưa tăng do TikTok CDN cache phân tán:
   - Truy vấn follower của các nick đích trong mảng `followed` của `follow_result.json`:
     ```python
     # Ví dụ: M17 follow hang.bui813 và yaelmssp62p
     # hang.bui813 tăng từ 58 lên 59 (+1)
     # yaelmssp62p tăng từ 24 lên 25 (+1)
     ```
   - Nếu follower các nick đích tăng khớp với các lượt follow của runner, kết luận lượt follow thành công 100%, web counter nick cày chỉ bị trễ hiển thị.
