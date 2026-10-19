# Row-Level Follow Historical Audit & SQLite Schema Playbook

## 1. Chu kỳ điều phối & Định nghĩa "Cùng kỳ" của Row
- **Chu kỳ 4 ngày (4-Day Parity Cycle):** 
  - N1 (ngày lẻ): Row 1 chạy Ca 1 (06:00 Phiên 1, 08:00 Phiên 2).
  - N2 (ngày chẵn): Row 2 chạy Ca 1 (06:00 Phiên 1, 08:00 Phiên 2).
  - N3: Row 7, Row 8.
  - N4: Dưỡng (0 follow + up video).
- **Quy tắc so sánh "Cùng kỳ" (Same-Period Comparison):**
  - Khi user yêu cầu so sánh Row 1 (hoặc Row 2) với "cùng kỳ các hôm trước", đối chiếu trực tiếp với các mốc **N - 4 ngày, N - 8 ngày, N - 12 ngày...** (ví dụ: ngày 19/10 so với 15/10, 11/10, 07/10, 03/10).
  - Không so sánh với ngày liền kề (N-1) vì ngày N-1 chạy Row 2 hoặc Row dưỡng.

---

## 2. Schema Dữ liệu Lịch sử Follow (`tiktok_tracker.db`)
Database đặt tại: `D:/Taadaa/data/tiktok_tracker.db` (chỉ mở dạng read-only `file:...?mode=ro` khi query).

### A. Bảng ánh xạ tài khoản và phân Row
- `farm_account_info`:
  - `username` (TEXT), `may` (INTEGER), `tik` (INTEGER - Slot/Row: `tik=1` là Row 1), `host_id` (TEXT: `'kibe'` máy 1-80, `'admin'` máy 201-280).
- `account_mapping`:
  - `username` (TEXT), `may` (INTEGER), `tik` (INTEGER).

### B. Bảng hành động và sản lượng Follow
- `daily_account_actions`:
  - `target_date` (TEXT, format `YYYY-MM-DD`).
  - `username` (TEXT), `may` (INTEGER).
  - `internal_follows` (INTEGER) - số follow chéo bot nội bộ trong ngày.
  - Dùng để tính tổng sản lượng follow thực tế của từng tài khoản, tỷ lệ nick chạy thành công (>0) và năng suất trung bình (avg/max).
- `session_account_actions`:
  - `session_key` (TEXT, e.g. `2026-10-19_ca1_phien1`, `2026-10-19_ca1_phien2`).
  - `target_date` (TEXT), `username` (TEXT), `may` (INTEGER), `internal_follows` (INTEGER).
  - Dùng để bóc tách sản lượng và số nick tham gia theo từng phiên (Phiên 1 lúc 06:00 vs Phiên 2 lúc 08:00).
- `session_action_stats`:
  - `session_key` (TEXT), `cluster` (TEXT: `kibe` / `admin`).
  - `internal_follows` (INTEGER), `natural_follows` (INTEGER - follow 1% feed tự nhiên), `likes`, `swipes`.

---

## 3. Query Mẫu O(1) Cho Báo Cáo Đối Soát Cùng Kỳ

```sql
-- 1. Sản lượng theo ngày của Row 1 qua các kỳ
SELECT 
    d.target_date,
    count(distinct d.username) as active_accounts,
    sum(d.internal_follows) as total_internal_follows,
    round(avg(d.internal_follows), 1) as avg_per_account,
    max(d.internal_follows) as max_per_account
FROM daily_account_actions d
JOIN farm_account_info f ON d.username = f.username
WHERE f.tik = 1
GROUP BY d.target_date
ORDER BY d.target_date DESC;

-- 2. Bóc tách theo từng Phiên (P1 vs P2) của Row 1
SELECT 
    s.target_date,
    s.session_key,
    count(distinct s.username) as acc_count,
    sum(s.internal_follows) as follows
FROM session_account_actions s
JOIN farm_account_info f ON s.username = f.username
WHERE f.tik = 1 AND s.session_key LIKE "%ca1%"
GROUP BY s.target_date, s.session_key
ORDER BY s.target_date DESC, s.session_key ASC;
```

---

## 4. Triage Hiện Trường State & Cooldown (Tù)
- Thư mục state per-account: `D:/Taadaa/tiktok-follow/runs/state/follow_state_{machine}_row_{row}.json`
- Khi kiểm tra tỷ lệ nick bị rớt khỏi dàn (dropped accounts):
  1. Kiểm tra `last_cooldown_decision`:
     - `streak`: số lần vi phạm liên tiếp.
     - `cooldown_until_date`: ngày hết hạn tù.
     - `decided_at`: timestamp quyết định cooldown.
  2. Kiểm tra `last_failed_date` & `fail_streak`:
     - Nếu `streak > 0`, nick bị giới hạn ngân sách warm-up (3-5 follow) hoặc bị cách ly tạm dừng follow.
  3. Runtime logs:
     - `D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/row-1-HHMMSS/` chứa `machines/machine_XX/TIMESTAMP/follow_result.json`.
     - Phân loại lỗi: `follow-released-daily-cooldown` (đang chịu phạt tù cũ) vs `FOLLOW_FAILED: anchor @... bị nhả sau vuốt` (mới dính nhả trong ca sáng).
