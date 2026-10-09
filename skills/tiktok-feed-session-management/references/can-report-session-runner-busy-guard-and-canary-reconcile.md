# Watchdog Session Reporting Guard & Canary Follow Reconciliation

## 1. Guard `runner_busy` trong `can_report_session()`

### Vấn đề & Pitfall
Trước đây, logic kiểm tra `completed_expected_count >= expected_count` được đặt ở đầu hàm `can_report_session()`. 
Khi toàn bộ 80 máy vừa hoàn tất lướt feed, `completed_expected_count` đạt đủ 80 máy nhưng các worker vẫn đang bận chạy follow hook, upload hook, hoặc ghi log artifact (`runner_busy = True`).
Nếu watchdog chốt phiên sớm tại thời điểm này:
- Báo cáo phát ra thiếu số liệu follow thật hoặc upload.
- Đánh rớt các test case trong bộ `test_feed_session_watchdog.py` (ví dụ `test_can_report_session` yêu cầu `assertFalse` khi `runner_busy=True` bất kể đủ 80 máy).

### Code Contract Chuẩn
Guard `if is_today and runner_busy: return False` BẮT BUỘC phải nằm ở ĐẦU TIÊN của hàm `can_report_session`:

```python
def can_report_session(
    is_today: bool,
    completed_expected_count: int,
    expected_count: int,
    now_hm: str,
    window_end_hm: str,
    runner_busy: bool,
    has_unattempted_locked: bool = False,
    latest_run_minutes_ago: float = None,
) -> bool:
    """Xác định điều kiện chốt báo cáo cho một phiên."""
    # Nếu đang trong ngày hôm nay và runner/uploader vẫn đang bận: TUYỆT ĐỐI KHÔNG chốt sớm
    if is_today and runner_busy:
        return False

    # Nếu tất cả máy dự kiến đã hoàn tất thật (không còn lock dở dang): chốt ngay
    if completed_expected_count >= expected_count and not has_unattempted_locked:
        return True
    ...
```

---

## 2. Canary Follow Reconciliation (`reconcile_cluster_following`)

### Cơ chế hoạt động
`reconcile_cluster_following` thực hiện đối soát số lượt follow thực tế trên TikTok Web so với số liệu kịch bản follow hook báo cáo:
1. Đọc mapping tài khoản từ workbook (`account_workbook`).
2. Tự động gọi script cào hồ sơ tài khoản: `python D:/Taadaa/tools/tiktok_account_tracker.py --usernames <username>`.
   *(Lưu ý: Bắt buộc script watchdog phải có `import subprocess` để không bị lỗi `NameError: name 'subprocess' is not defined`).*
3. Đọc dữ liệu từ SQLite DB `D:/Taadaa/data/tiktok_tracker.db` (bảng `snapshots`, cột `following`, `timestamp`, `id` theo `ORDER BY timestamp DESC, id DESC LIMIT 2`).
4. Tính độ chênh lệch delta giữa `rows[0]` (snapshot mới nhất vừa cào) và `rows[1]` (snapshot mốc trước phiên) để so với `script báo`.
5. Đưa ra dòng kết luận:
   `+ Đối soát TikTok Web (+N Following thật - Khớp 100% so với script báo):`
   `- M{m} (@{u}): script báo {cnt} | web tăng +{delta} (Khớp 100%)`
