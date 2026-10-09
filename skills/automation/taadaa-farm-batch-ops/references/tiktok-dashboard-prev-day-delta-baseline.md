# TikTok Dashboard Delta Tracking & Baseline Architecture

## 1. Context & Business Problem
Trong dashboard theo dõi nick TikTok farm (`tiktok_dashboard.py`), các chỉ số delta (`delta_follower`, `delta_heart`, `delta_following`, `delta_video`) hiển thị mức độ tăng trưởng của từng tài khoản.

Khi hệ thống quét snapshot nhiều lần trong cùng 1 ngày (ví dụ 10:00, 11:00, 12:00):
- Nếu chỉ so sánh giữa `rn = 1` và `rn = 2` (snapshot gần nhất trước đó), các lần quét liên tiếp trong ngày chỉ cho delta so với lần quét vừa xong vài chục phút trước (thường là +0 hoặc +1), làm mất ý nghĩa theo dõi tăng trưởng trong ngày (Daily Growth).
- Khi có dữ liệu ngày hôm trước (`has_prev_day`), mốc so sánh chuẩn phải là snapshot **muộn nhất của ngày gần nhất trước ngày hiện tại** (`LatestPrev` với `timestamp < max_dt`).

## 2. SQL Contract (CTE Architecture)
Khi truy vấn snapshots từ `tiktok_tracker.db`:

```sql
SELECT substr(MAX(timestamp), 1, 10) FROM snapshots; -- max_dt
SELECT substr(MAX(timestamp), 1, 10) FROM snapshots WHERE substr(timestamp, 1, 10) < ?; -- row_prev
```

### Trường hợp 1: Có dữ liệu ngày hôm trước (`has_prev_day = True`)
Sử dụng 2 CTE:
- `LatestCurr`: Lấy bản ghi snapshot mới nhất trong ngày hiện tại cho mỗi username (`rn = 1` partition by username order by timestamp DESC, where `substr(timestamp, 1, 10) = ?`).
- `LatestPrev`: Lấy bản ghi snapshot cuối cùng trước ngày hiện tại cho mỗi username (`rn = 1` partition by username order by timestamp DESC, where `substr(timestamp, 1, 10) < ?`).
- Left join `LatestCurr r1` với `LatestPrev r2` trên `r1.username = r2.username AND r2.rn = 1`.

### Trường hợp 2: Chưa có ngày hôm trước (`has_prev_day = False`) - Single-day Fallback
Sử dụng ranking truyền thống:
- CTE `Ranked` partition by username order by timestamp DESC.
- Left join `r1` (với `rn = 1`) và `r2` (với `rn = 2`) để so sánh giữa 2 lần quét gần nhất nếu có.

## 3. Unit Test Validation Pattern
Trong `tests/test_tiktok_dashboard.py`, test case kiểm chứng logic này phải mô phỏng tối thiểu 3 snapshots qua 2 ngày:
- Ngày 1: `2024-01-01 10:00:00` (follower=10, heart=20)
- Ngày 2 scan 1: `2024-01-02 10:00:00` (follower=15, heart=30)
- Ngày 2 scan 2: `2024-01-02 12:00:00` (follower=16, heart=31)

Kỳ vọng:
- Delta Follower của Day 2 scan 2 phải là `16 - 10 = +6` (so với mốc Day 1), KHÔNG PHẢI `16 - 15 = +1`.
- Delta Heart phải là `31 - 20 = +11`.
