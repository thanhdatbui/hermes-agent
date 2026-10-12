# Watchdog Session-End Clamping & Historical Backfill Reconcile

## Hiện Tượng Lệch Ảo Khi Watchdog Quét Bù (Historical Backfill Window Bug)
Khi `feed_session_watchdog.py` hoặc `follow_session_watchdog.py` khởi chạy (hoặc được thêm mới qua cron), nó sẽ quét lại các phiên chưa được đánh dấu hoàn tất trong cửa sổ lưu trữ 7 ngày (`retention_cutoff = 7 days`).
Nếu một ca từ nhiều ngày trước (ví dụ `2026-10-05_ca1_phien1`) được kích hoạt quét bù:
- **Baseline Snapshot (`baseline_row`):** Truy vấn đúng snapshot trước giờ bắt đầu của ca đó (`timestamp <= session_start_iso`, tức dữ liệu trước 06:00 ngày 05/10).
- **Latest Snapshot (`latest_row`) thiếu chặn trần:** Nếu query chỉ lấy `ORDER BY timestamp DESC LIMIT 2`, nó sẽ bốc trúng snapshot **tại thời điểm hiện tại của hôm nay** (ví dụ 12/10), thay vì snapshot lúc ca đó kết thúc.
- **Hậu quả:** 
  + `web_delta = latest_fl - prev_fl` đo lường mức tăng trưởng tích lũy của **suốt 7 ngày (04/10 đến 12/10)** (+129 following thật).
  + Đem so sánh với số lượt follow của **duy nhất 1 phiên cũ** (script báo 67 lượt).
  + Báo cáo trên Telegram xuất hiện độ lệch khổng lồ: `Lệch +62 so với script báo 67`, khiến người vận hành lầm tưởng bot đang bị lỗi chạy loạn follow tự nhiên trên dàn máy.
  + Thêm vào đó, nếu tiêu đề báo cáo không gắn tag ngày `[target_date]`, người dùng sẽ hiểu nhầm đây là ca sáng của ngày hôm nay.

---

## Kiến Trúc Sửa Đổi Bắt Buộc Trong `feed_session_watchdog.py`

### 1. Thêm tham số `session_end_iso` vào chữ ký hàm `reconcile_cluster_following`:
```python
def reconcile_cluster_following(
    cluster: dict[str, Any],
    fl_success: list,
    all_follows: dict,
    active_row: int,
    session_start_iso: Optional[str] = None,
    session_end_iso: Optional[str] = None,  # Bắt buộc có để chặn trần snapshot
    db_path: str = r"D:/Taadaa/data/tiktok_tracker.db",
    ...
) -> list[str]:
```

### 2. Logic truy vấn Snapshot giới hạn cửa sổ phiên:
```python
if session_end_iso:
    cur.execute("""
        SELECT following, timestamp
        FROM snapshots
        WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
        ORDER BY timestamp DESC, id DESC
        LIMIT 1
    """, (u, session_end_iso))
    l_rows = cur.fetchall()
    latest_row = l_rows[0] if l_rows else None
else:
    cur.execute("""
        SELECT following, timestamp
        FROM snapshots
        WHERE LOWER(username) = LOWER(?)
        ORDER BY timestamp DESC, id DESC
        LIMIT 2
    """, (u,))
    pair = cur.fetchall()
    latest_row = pair[0] if len(pair) >= 1 else None
```

### 3. Tính toán trần kết thúc phiên tại điểm gọi (`main()`):
```python
end_time_str = "23:59:59" if win["end"] in {"24:00", "00:00"} else f"{win['end']}:00"
reconcile_lines = reconcile_cluster_following(
    cluster, fl_success, all_follows, active_row,
    session_start_iso=f"{target_date} {win['start']}:00",
    session_end_iso=f"{target_date} {end_time_str}",
    all_machines=all_machines,
    session_key=session_key,
)
```

---

## Quy Tắc Đồng Bộ Gương (Mirror Invariant)
Trong repo `tiktok-luot nuoi acc`:
- Bất kỳ chỉnh sửa nào trên `scripts/feed_session_watchdog.py` **BẮT BUỘC PHẢI COPY NGUYÊN VẸN** sang file mirror `scripts/hermes_cron/feed_session_watchdog.py`.
- Hai file này bắt buộc phải khớp byte-for-byte (`diff -u` trả về rỗng) để đảm bảo môi trường runner và cronjob thực thi đồng nhất.
- Kiểm chứng luôn chạy đồng thời 2 file test:
  ```bash
  pytest python_runner/tests/test_feed_session_watchdog.py python_runner/tests/test_follow_session_watchdog.py
  ```
