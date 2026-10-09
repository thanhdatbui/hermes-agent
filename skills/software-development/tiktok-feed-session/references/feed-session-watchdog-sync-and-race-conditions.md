# Feed Session Watchdog Synchronization & Race Condition Guard

## 1. Đồng Bộ 3 Bản Sao Của `feed_session_watchdog.py`
Hệ thống duy trì 3 bản sao của `feed_session_watchdog.py`:
1. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` (Hermes live runtime đang chạy cron)
2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py` (Mẫu deploy đồng bộ đa máy)
3. `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py` (Source authority trong repo consumer)

### Pitfall Drift:
- Bản sao trong consumer repo (`tiktok-luot nuoi acc`) có thể bị trễ so với runtime/deploy (thiếu `_add_minutes_to_hm`, `grace_end_hm`, `has_unattempted_locked`, dynamic runtime root).
- Mọi bản vá logic watchdog bắt buộc phải áp dụng đồng bộ trên cả 3 file để đảm bảo logic identical và test suite `test_feed_session_watchdog.py` phản ánh đúng môi trường chạy thật.

## 2. Race Condition Trong `can_report_session`
### Nguyên nhân lỗi:
Nếu kiểm tra `completed_expected_count >= expected_count` trước khi kiểm tra `now_hm < window_end_hm`, watchdog sẽ chốt báo cáo sớm ngay khi số máy đạt chỉ tiêu, bất chấp việc feed runner hoặc follow hook đang chạy dở các máy còn lại / retry.

### Thứ tự điều kiện chuẩn xác:
```python
def can_report_session(
    is_today: bool,
    completed_expected_count: int,
    expected_count: int,
    now_hm: str,
    window_end_hm: str,
    runner_busy: bool,
    has_unattempted_locked: bool = False,
) -> bool:
    \"\"\"Xác định điều kiện chốt báo cáo cho một phiên.\"\"\"
    # 1. Đang trong giờ phiên: kiểm tra runner_busy trước tiên
    if is_today and now_hm < window_end_hm:
        if runner_busy:
            return False
        if has_unattempted_locked:
            return False
        return completed_expected_count >= expected_count

    # 2. Tất cả máy dự kiến đã hoàn tất thật (ngoài giờ hoặc runner đã idle): chốt ngay
    if completed_expected_count >= expected_count and not has_unattempted_locked:
        return True

    # 3. Khi đã qua window_end_hm: grace period tối đa 20 phút nếu runner đang chạy
    if is_today:
        grace_end_hm = _add_minutes_to_hm(window_end_hm, 20)
        if runner_busy and now_hm < grace_end_hm:
            return False
        return True

    return (completed_expected_count >= expected_count) or (now_hm >= "02:00")
```

## 3. Phân Nhóm Follow Success & Xử Lý Skipped
- **Skipped classification:** Khi kết quả follow có status thuộc `{"OK", "SUCCESS"}` nhưng `len(followed) == 0`, phải phân loại vào `fl_skipped` thay vì xem là thành công `fl_success`.
- **Format success follows:** Dùng helper `format_success_follows(fl_success, all_follows)` để phân loại theo nhóm:
  - 1 - 4 lượt
  - 5 - 9 lượt
  - 10+ lượt
- **Unit test boundary:** Khi cập nhật `grace_end_hm`, unit test `test_can_report_session_production_helper` cần lưu ý:
  - Nếu `now_hm` quá `window_end_hm` nhưng chưa quá 20 phút (`now_hm < grace_end_hm`) và `runner_busy=True`, hàm sẽ trả về `False` (đang trong grace period).
  - Chỉ khi `runner_busy=False` hoặc `now_hm >= grace_end_hm` thì mới trả về `True`.
