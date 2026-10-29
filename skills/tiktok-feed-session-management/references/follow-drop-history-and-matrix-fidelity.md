# Follow Drop History & Dashboard Matrix Fidelity

## Bối cảnh sự cố
Trong hệ thống Farm TikTok (`follow_runner` & `tiktok_dashboard`):
1. Khi tài khoản gặp sự cố nhả follow / cooldown (ví dụ dính bẫy anchor check sau vuốt), runner gọi `set_follow_failed()`.
2. Trước đây `follow_state.py` chỉ lưu các trường đơn lẻ:
   - `last_failed_date`: ngày fail gần nhất (ghi đè ngày cũ).
   - `last_failed_at`: timestamp fail gần nhất (ghi đè timestamp cũ).
   - `fail_streak`: số lần fail liên tiếp (streak 1, 2, 3...).
3. Khi nick bị nhả follow ngay từ đầu phiên (`used == 0` lượt thành công):
   - Danh sách `followed` không có bất kỳ UID nào của ngày đó.
   - Khi streak tăng lên (Streak 2, 3...), các ngày fail trước đó bị `last_failed_date` ghi đè mất hoàn toàn.
   - Sổ bệnh án (`get_account_follow_detail`) chỉ bốc ngày từ `followed`, nên ngày nhả cũ biến mất, dẫn tới hiện tượng nick Streak = 2 hoặc 3 nhưng Sổ bệnh án chỉ hiện 1 ca chạy duy nhất.

## Giải pháp kiến trúc

### 1. Runner Core (`follow_runner/core/follow_state.py`)
Khi gọi `set_follow_failed()`, bắt buộc lưu mảng `drop_history`:
```python
hist = self._data.setdefault("drop_history", [])
if not any(isinstance(x, dict) and x.get("date") == today for x in hist):
    hist.append({"date": today, "streak": streak, "timestamp": now_iso})
    if len(hist) > 30:
        hist.pop(0)
```
- Đảm bảo mỗi ca chạy bị fail/nhả follow đều được lưu lại thành một entry độc lập với ngày và streak cụ thể, không bị ghi đè khi streak tăng.

### 2. Dashboard Follow Detail Component (`follow_health_helper.py`)
Trong hàm `get_account_follow_detail`:
- Phải duyệt qua cả `drop_day` gần nhất và mảng `drop_history`:
```python
if drop_day and drop_day not in daily:
    daily[drop_day] = 0

drop_dates = set([drop_day] if (drop_day and is_in_cooldown) else [])
for dh in d.get("drop_history", []):
    if isinstance(dh, dict) and dh.get("date"):
        dh_d = str(dh["date"])
        drop_dates.add(dh_d)
        if dh_d not in daily:
            daily[dh_d] = 0

daily_matrix = [
    {"date": day, "count": daily[day], "is_drop": bool(day in drop_dates)}
    for day in sorted(daily.keys(), reverse=True)[:14]
]
```
- Đảm bảo ngày bị nhả luôn xuất hiện trong ma trận ca chạy của nick (với `count = 0` và `is_drop = True`), thể hiện rõ ràng chip đỏ cảnh báo `🛑 0 lượt` cho từng ca fail trong quá khứ.
