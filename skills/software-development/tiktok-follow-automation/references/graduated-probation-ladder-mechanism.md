# Graduated Probation (Bậc thang thử thách 3 nấc) cho Nick có tiền án nhả follow

## 1. Khái niệm & Cơ chế
Đối với nick TikTok bị phạt nhả follow (`fail_streak > 0`), khi mãn hạn cooldown sẽ không được quay lại ngay full budget 100% (`_range(1) = 10-20`), mà phải đi qua lộ trình thử thách 3 nấc dựa trên số ngày chạy sạch tích lũy (`probation_clean_days`):

- **Nấc 1 (Mới ra tù, probation_clean_days < 3):**
  - Budget: `random.randint(3, 5)` lượt/phiên.
  - Mode telemetry: `probation_tier1`.
- **Nấc 2 (Đã chạy sạch 3 ngày, 3 <= probation_clean_days < 6):**
  - Budget: `random.randint(7, 9)` lượt/phiên.
  - Mode telemetry: `probation_tier2`.
- **Nấc 3 (Tốt nghiệp, probation_clean_days >= 6):**
  - Đã tích lũy đủ 6 ngày follow thành công mà không bị nhả lại.
  - `fail_streak` được reset về 0, xóa `probation_clean_days`.
  - Quay lại trạng thái bình thường: `mode = "full"`, budget = `_range(1)` (10-20 lượt/phiên).

## 2. Quy tắc vòng đời dữ liệu trong FollowState
1. **Trong ngày follow thành công (`mark(uid, STATUS_FOLLOWED)`):**
   - Nếu `fail_streak > 0`: lưu `recovered_date = today`. Không xóa `fail_streak` ngay trong ngày để giữ nguyên chế độ thử thách cho các phiên tiếp theo cùng ngày.
2. **Qua ngày mới (`_roll_day()`):**
   - Nếu có `recovered_date < today`: tăng `probation_clean_days += 1`, xóa `recovered_date`.
   - Nếu `probation_clean_days >= 6`: xóa án tích (`fail_streak = 0`), xóa `probation_clean_days`.
3. **Khi bị phạt nhả follow (`set_follow_failed()`):**
   - Xóa `recovered_date` và xóa `probation_clean_days` (đưa ngày sạch về 0 ngay lập tức, reset về vạch xuất phát).
4. **Khi reset thủ công (`reset_follow_failed()`):**
   - Xóa `recovered_date`, `probation_clean_days`, đặt `fail_streak = 0`.
