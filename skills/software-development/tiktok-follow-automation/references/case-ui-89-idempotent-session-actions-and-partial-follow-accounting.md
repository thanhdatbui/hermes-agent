# Case UI-89: Idempotent Session Staging & Bảo Toàn Lượt Bấm Trước Khi Nhả Follow

## 1. Bối cảnh & Hiện tượng (2026-10-03)
Trên TikTok Farm Dashboard, số lượng **🔗 Nội bộ (+49, +42, +39...)** bị hiển thị vượt xa số lượng **Đã follow (+32, +27, +23...)** cào từ profile TikTok Web.

User phản ánh 2 điểm mấu chốt:
1. *Mỗi nick chỉ chạy đúng 1 ca/ngày trong slot của nó, không có chuyện cộng dồn bừa bãi.*
2. *Bộ đếm trừ nhả là do chính script trên máy bắt và tính toán độc lập tại hiện trường để đối soát với Web.*
3. *Nếu máy bấm được N lượt (ví dụ 3 lượt) rồi mới bị nhả (follow_failed=True), thì N lượt đã bấm thành công BẮT BUỘC PHẢI ĐƯỢC TÍNH, cấm tự ý xóa bỏ.*

---

## 2. Root Cause Analysis

### Bug 1: Watchdog Cron 5 Phút Gây Cộng Lặp Non-Idempotent (Nhân 3)
* Trong `feed_session_watchdog.py`, hàm `reconcile_cluster_following` ghi trực tiếp vào `daily_account_actions`:
  ```sql
  ON CONFLICT(target_date, username) DO UPDATE SET
      internal_follows = daily_account_actions.internal_follows + excluded.internal_follows
  ```
* Khi một phiên kết thúc ở cụm Kibe nhưng chưa gửi báo cáo ngay (chờ cụm Admin), cron 5 phút quét qua nhiều lần. Mỗi lần quét lại thực hiện phép cộng `+ excluded.internal_follows`, khiến số follow của Phiên 1 bị nhân 3 lần ($10 \rightarrow 30, 14 \rightarrow 42$).

### Bug 2: Gate `target_machines` Bỏ Quên Các Máy Bị Nhả Sau Khi Đã Bấm Vài Lượt
* Trong `reconcile_cluster_following`:
  ```python
  target_machines = {str(m) for m in fl_success} | set(natural_targets)
  ```
* Khi một máy bấm được $N > 0$ lượt rồi mới dính lỗi nhả (ví dụ M38 bấm 3 lượt thì dính nhả), `classify_machine_follow_result` xếp nó vào `fl_released` (thay vì `fl_success`).
* Do không nằm trong `fl_success`, máy bị loại hoàn toàn khỏi `target_machines` nếu không có follow tự nhiên, dẫn đến $N$ lượt bấm thành công bị vứt bỏ oan uổng.

### Bug 3: Ghi Thiếu Follow Tự Nhiên Vào DB (Lệch Giữa Telegram Report & Dashboard)
* Trong `reconcile_cluster_following` (dòng 1111):
  ```python
  c_cnt = 0 if is_failed else m_to_cross.get(str(m_num), 0)  # <-- SAI: CHỈ LẤY CHÉO!
  ```
* Dù trên tin nhắn Telegram đã tính đầy đủ `m_to_reported = cnt + natural_cnt` (chéo + tự nhiên hợp lệ), nhưng khi ghi vào `session_account_actions` để rollup lên `daily_account_actions`, code lại chỉ ghi `m_to_cross`.
* Hậu quả: Dashboard đọc `daily_account_actions.internal_follows` bị thiếu mất toàn bộ các lượt follow tự nhiên (M9 hiện +29 thay vì +32, M38 hiện +12 thay vì +14, M52 hiện +9 thay vì +12), khiến cột "🔗 Nội bộ" lệch vài số so với Web tăng thật.
* **Khắc phục**: Dùng đúng `m_to_reported.get(str(m_num), 0)`:
  ```python
  c_cnt = 0 if is_failed else m_to_reported.get(str(m_num), 0)
  ```


---

## 3. Kiến Trúc Khắc Phục Chuẩn

### A. Idempotent Session Staging Table
Tách việc ghi nhận từng phiên khỏi bảng tổng hợp ngày:
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
* Trong mỗi tick watchdog, ghi đè idempotent:
  ```sql
  INSERT INTO session_account_actions ...
  ON CONFLICT(session_key, cluster, username) DO UPDATE SET
      internal_follows = excluded.internal_follows,
      updated_at = excluded.updated_at
  ```
* Bảng `daily_account_actions` được tính bằng `SUM(internal_follows)` theo các phiên riêng biệt của ngày:
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

### B. Mở Rộng `target_machines` Nhận Diện Mọi Máy Có Lượt Bấm
```python
target_machines = (
    {str(m) for m in fl_success}
    | {str(m) for m, fd in all_follows.items() if isinstance(fd, dict) and len(fd.get("followed") or []) > 0}
    | set(natural_targets)
)
```

### C. Quy Tắc Kỷ Luật Đếm Lượt Bị Nhả & Khấu Trừ Follow Tự Nhiên (User Invariant 2026-10-03)
Khi máy bị lỗi `follow_failed = True` (bị nhả follow giữa chừng hoặc TikTok không nhận follow):
1. **Nếu follow chéo lượt đầu tiên = 0 (`cnt == 0`):**
   - TikTok chưa nhận bất kỳ follow nào từ máy này -> coi như nick bị nhả/drop hoàn toàn.
   - **Xử lý:** Bỏ toàn bộ follow tự nhiên và chéo của máy này (`reported = 0`).
   - Hàm `calculate_session_natural_follows`: Tự động trừ sạch các lượt follow tự nhiên của máy này khỏi tổng phiên để triệt tiêu hoàn toàn delta âm ảo.
2. **Nếu lượt đầu tiên follow chéo đã thành công (`cnt > 0`):**
   - TikTok ĐÃ ghi nhận các lượt follow trước đó (ví dụ M52 ăn 9 lượt chéo, M70 ăn 4 lượt chéo).
   - **Xử lý:** Tính HẾT toàn bộ follow tự nhiên thành công (`natural_cnt`) + các lượt chéo đã bấm thành công cho tới thời điểm bị ngắt phiên (`reported = cnt + natural_cnt`).
   - Hàm `calculate_session_natural_follows`: KHÔNG trừ follow tự nhiên của máy này.
   - Ghi nhận đầy đủ vào `daily_account_actions` và đối soát Web chính xác, loại bỏ hiện tượng báo lệch ảo.

### D. Multi-Cluster Rollup & Telemetry Observability
- **Rollup chống phân mảnh**: Khi rollup từ `session_account_actions` lên `daily_account_actions`, BẮT BUỘC `GROUP BY target_date, username` (thay vì group cả `may`) và dùng `MAX(may), SUM(internal_follows)` để đảm bảo một tài khoản chạy qua nhiều máy hoặc cả 2 cụm (Kibe/Admin) được cộng dồn chính xác.
- **Structured Telemetry & DB Error Resilience**: Reconcile BẮT BUỘC ghi log `[FOLLOW_RECONCILE_TELEMETRY]` với đầy đủ `session_key`, `cluster`, `audited_accounts`, `reported_follows`, `scraped_delta`, `diff` và có khối `try/except` rollback an toàn khi database bận/khóa.
