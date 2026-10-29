# Follow Matrix & Detail Modal Zero-Follow Drop Pitfall

## 1. Hiện tượng & Vấn đề thực tế
- Người dùng mở **Sổ bệnh án** của tài khoản TikTok trên Dashboard (cổng 1905) hoặc xem ma trận ca chạy gần đây:
  - Tài khoản đang có `fail_streak` = 2, 3 (hoặc đang dính án phạt cooldown, tier Cooldown đỏ).
  - Nhưng trong popup Sổ bệnh án (`follow_detail_component.py`) hoặc ma trận ca chạy chỉ hiển thị 1 ngày chạy duy nhất (thường là ngày có follow thành công cũ) mà **không thấy hiển thị chip đỏ báo nhả follow** (`🛑 lượt`) của ngày bị nhả gần nhất.
  - Người dùng thắc mắc: *"Sao nick streak 2, streak 3 mà lịch sử chỉ ghi có 1 ca / không thấy lịch sử đi follow bị nhả?"*

## 2. Nguyên nhân kỹ thuật gốc rễ (Root Cause)
1. **Lệch pha giữa Overview Health Table (`get_follow_health_data`) và Account Detail (`get_account_follow_detail`):**
   - Trong `get_follow_health_data`, danh sách ngày ma trận (`matrix_dates`) được sinh từ tập hợp `all_run_dates`, trong đó có thêm `drop_day` (ngày xảy ra lỗi / cooldown).
   - Tuy nhiên, trong `get_account_follow_detail` (file `follow_health_helper.py`), ma trận ca chạy của nick (`daily_matrix`) chỉ được tính từ `followed` (danh sách UID follow thành công) và `history`.
   - Khi một phiên follow bị nhả ngay từ đầu (ví dụ: dính bẫy anchor check sau khi vuốt hoặc ăn cooldown ngay lượt đầu), số follow thành công `used == 0`. Do không có UID nào được ghi vào `followed`, từ điển `daily` không có key `drop_day`.
   - Vòng lặp `daily_matrix = [{"date": day, ...} for day in sorted(daily.keys())]` hoàn toàn bỏ qua ngày bị nhả, khiến popup Sổ bệnh án nuốt chửng sự kiện nhả follow!

2. **Cơ chế lưu trữ State File (`follow_state_<machine>_row_<row>.json`):**
   - Trong `follow_runner/core/follow_state.py`, runner chỉ lưu đúng 1 trường `last_failed_date` và `last_fail_reason` cho lần fail gần nhất.
   - Mỗi lần fail liên tiếp trong `grace_window`, runner tăng `fail_streak += 1` và ghi đè `last_failed_date` thành ngày hiện tại.
   - Do không có mảng lịch sử `drop_history: []`, ngày fail của các streak trước đó bị ghi đè, khiến hệ thống chỉ có thể tái hiện được đúng 1 ngày fail gần nhất và các ngày có follow thành công.

## 3. Bản vá khắc phục (Contract Chuẩn O(1))
Tại `D:/Taadaa/tools/follow_health_helper.py` trong hàm `get_account_follow_detail`:
Đảm bảo nếu tài khoản đang có `drop_day` (đang cooldown hoặc `fail_streak > 0`), nếu `drop_day` chưa có trong `daily`, bắt buộc chèn `daily[drop_day] = 0`:

```python
    if is_in_cooldown:
        # ... xác định drop_day từ last_failed_at / last_cooldown_decision / last_failed_date ...
        if not drop_day:
            drop_day = (d.get("last_failed_date") or d.get("follow_failed_date") or "")[:10] or None
        if drop_day and drop_day not in daily:
            daily[drop_day] = 0

    daily_matrix = [
        {"date": day, "count": daily[day], "is_drop": bool(day == drop_day and is_in_cooldown)}
        for day in sorted(daily.keys(), reverse=True)[:14]
    ]
```

## 4. Kiểm chứng & Restart Service
- Chạy unit test: `python -m pytest D:/Taadaa/tools/tests/test_tiktok_dashboard.py -k test_follow_detail_api`
- Restart TikTok Dashboard: `python D:/Taadaa/tools/restart_tiktok_dashboard.py`
- Test API thực tế: Gọi `http://127.0.0.1:1905/api/follow-detail?machine=<M>&row=<R>` và xác nhận `daily_matrix` trả về đúng chip `{"date": drop_day, "count": 0, "is_drop": True}`.
