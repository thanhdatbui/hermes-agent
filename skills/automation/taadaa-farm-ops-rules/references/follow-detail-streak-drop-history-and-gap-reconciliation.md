# Lịch Sử Ca Follow & Khế Ước Ghi Nhận Drop History Toàn Diện

## 1. Vấn Đề Gốc Rễ (Root Cause: Thiếu Mảng Lịch Sử Thất Bại)
Trước đây, file `follow_state_<machine>_row_<row>.json` và hệ thống theo dõi Dashboard gặp 2 lỗi kiến trúc khiến ma trận ca chạy bị sai lệch:
1. **Thiếu Drop Day khi 0 Lượt Follow:**
   - Trong `follow_health_helper.py` (`get_account_follow_detail`), ma trận ca chạy `daily_matrix` chỉ quét qua danh sách UID trong dictionary `followed`.
   - Khi nick vừa vào cữ chạy thì bị dính bẫy Anchor check (nhả follow sau vuốt) hoặc bị chặn ngay từ đầu (`used == 0`), ca chạy đó không có bất kỳ UID nào được ghi nhận.
   - Do đó, ngày fail (`last_failed_date`) không hề tồn tại trong `daily`, khiến chip cảnh báo nhả follow (`🛑 0 lượt`) bị biến mất hoàn toàn trên popup Sổ bệnh án.
2. **Ghi Đè Ngày Thất Bại Khi Tăng Streak (Overwrite on Escalation):**
   - Khi nick tái phạm và tăng streak (`fail_streak = 2, 3, 4`), runner chỉ cập nhật đè vào `last_failed_date` và `last_fail_reason`.
   - Các ngày fail của các streak trước đó hoàn toàn bị xóa dấu vết. Kết quả là nick có Streak 2 hoặc 3 nhưng Sổ bệnh án chỉ hiển thị đúng 1 ngày fail gần nhất, tạo cảm giác "cả tháng nick chỉ chạy 1 ca".

## 2. Giải Pháp Cơ Giới Hóa (Canonical Solution)
1. **Mảng `drop_history` Trong Runner State (`follow_runner/core/follow_state.py`):**
   - Trong hàm `set_follow_failed`, hệ thống khởi tạo và duy trì mảng `drop_history`:
     ```python
     hist = self._data.setdefault("drop_history", [])
     if not any(isinstance(x, dict) and x.get("date") == today for x in hist):
         hist.append({"date": today, "streak": streak, "timestamp": now_iso})
         if len(hist) > 30:
             hist.pop(0)
     self._save()
     ```
   - Mỗi lần nick bị nhả follow (dù ăn 0 lượt), ngày và streak tương ứng đều được ghi nhận vĩnh viễn vào lịch sử ca chạy.

2. **Khế Ước Hiển Thị Trong Sổ Bệnh Án (`tools/follow_health_helper.py`):**
   - Hàm `get_account_follow_detail` duyệt qua cả `drop_day` hiện tại lẫn toàn bộ mảng `drop_history`:
     ```python
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
   - Mọi ca fail đều được hiển thị dạng chip đỏ `🛑 0 lượt` tương ứng với ngày xảy ra sự cố.

## 3. Bản Chất Của Các Khoảng Cách "Cả Tháng Không Có Lượt Follow Mới"
Khi đối soát tài khoản thấy khoảng cách giữa các lần follow thành công cách nhau 20–30 ngày:
- **Không phải do nick bị bỏ quên**, mà do:
  1. Nick liên tục bị phạt cooldown dài ngày theo cơ chế lũy tiến (Streak 1: 3 ngày, Streak 2: 5–7 ngày, Streak 3: 7–11 ngày).
  2. Các ca chạy xen kẽ giữa tháng đều bị nhả follow ngay từ lượt đầu tiên (`used == 0`).
  3. Khi kết hợp với nhịp xoay tua phân ca 3 ngày ({1,2,7}, {3,4,8}, {5,6}), khoảng thời gian nick có lượt follow thành công thực tế bị giãn cách ra cả tháng.
