# Idempotent Session Account Actions & Anti-Duplicate Counting in Reconcile

## 1. Bối cảnh & Hiện tượng lỗi
Trong `feed_session_watchdog.py`, hàm `reconcile_cluster_following` chịu trách nhiệm đối soát số lượt follow thực tế trên TikTok Web và ghi nhận kết quả follow nội bộ (`internal_follows`) vào cơ sở dữ liệu `tiktok_tracker.db`.

Trước đây, code ghi thẳng vào bảng tổng ngày:
```sql
INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(target_date, username) DO UPDATE SET
    internal_follows = daily_account_actions.internal_follows + excluded.internal_follows,
    updated_at = excluded.updated_at
```

### Hậu quả nghiêm trọng:
Mỗi khi watchdog rescan, retry hoặc chạy lại phiên (hoặc đối soát lại trong cùng ngày), câu lệnh `daily_account_actions.internal_follows + excluded.internal_follows` sẽ cộng dồn lặp lại số lượt follow của chính phiên đó. Nếu watchdog chạy 3 lần, số follow bị thổi phồng x3.

## 2. Kiến trúc giải pháp chuẩn (Two-Tier Idempotent Ledger)

### Bước 1: Lưu chi tiết cấp phiên vào bảng trung gian
Tạo bảng `session_account_actions` với khóa chính tổng hợp `(session_key, cluster, username)`:
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
)
```

Khi ghi nhận kết quả từ phiên:
```sql
INSERT INTO session_account_actions (session_key, cluster, target_date, username, may, internal_follows, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(session_key, cluster, username) DO UPDATE SET
    internal_follows = excluded.internal_follows,
    updated_at = excluded.updated_at
```
-> Đảm bảo tính idempotent: Gọi n lần trong cùng 1 session cũng chỉ ghi đè đúng giá trị của session đó.

### Bước 2: Tái tổng hợp lên bảng ngày `daily_account_actions`
Sau khi upsert vào bảng trung gian, tính `SUM(internal_follows)` của đúng `(target_date, username)` trên toàn bộ các session trong ngày:
```sql
INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
SELECT target_date, username, may, SUM(internal_follows), ?
FROM session_account_actions
WHERE target_date = ? AND username = ?
GROUP BY target_date, username
ON CONFLICT(target_date, username) DO UPDATE SET
    internal_follows = excluded.internal_follows,
    updated_at = excluded.updated_at
```

## 3. Call Site & Signature Contract
- Chữ ký hàm `reconcile_cluster_following`: Bổ sung `session_key: Optional[str] = None`.
- Nơi gọi trong vòng lặp `SESSION_WINDOWS` của `feed_session_watchdog.py`: Bắt buộc truyền `session_key=session_key`.
- Khóa cluster: Lấy từ `cluster.get("name", "unknown")`.

## 4. Kiểm chứng Idempotency
Unit test `test_reconcile_cluster_following_idempotent_no_duplicate_counting`:
1. Gọi `reconcile_cluster_following` lần 1 với `session_key="2026-10-03_ca1_phien1"`, số follow = 3.
2. Query `daily_account_actions`: verify `internal_follows == 3`.
3. Gọi tiếp lần 2 và lần 3 với cùng `session_key` và dữ liệu đó.
4. Query lại `daily_account_actions`: verify `internal_follows == 3` (không bị cộng dồn thành 6 hay 9).

## 5. Kỷ luật đối soát bất biến: Bộ đếm trừ nhả từ Script & Cấm lấy DB đè ngược

1. **Bộ đếm trừ nhả thuộc thẩm quyền của Script:**
   - Cơ chế phát hiện nhả follow (`verify_follow`, cờ `follow_failed`, `fl_released`, khấu trừ natural follow khi dính cờ nhả) là do chính script trên điện thoại tự bắt và tự tính tại hiện trường.
   - **CẤM TUYỆT ĐỐI lấy số cào từ TikTok Web / Database để ghi đè hoặc tự trừ vào số nội bộ của script**: Mục đích cốt lõi của việc so sánh "Nội bộ" (từ script) vs "Đã follow" (từ TikTok Web) là để **kiểm chứng độc lập xem script trên máy có bắt nhả đúng hay không**. Nếu lấy số DB đè lại thì triệt tiêu hoàn toàn khả năng phát hiện lỗi của script.

2. **Quy tắc 1 nick chạy 1 ca (Slot Isolation):**
   - Mỗi nick trên farm chỉ chạy đúng 1 ca trong slot tương ứng của nó trong ngày.
   - Khi thấy số "Nội bộ" vọt lên bất thường vượt quá chỉ tiêu ca của nick đó (ví dụ 49 > 32 trong khi max per session là 20), đó là dấu hiệu 100% của bug cộng lặp non-idempotent trong tầng điều phối/watchdog. CẤM ngụy biện "do nick chạy nhiều ca cộng dồn" hay "do TikTok server âm thầm nhả follow". Bắt buộc đọc trực tiếp artifact `follow_result.json` của thiết bị để thấy số thực tế script đã báo.
