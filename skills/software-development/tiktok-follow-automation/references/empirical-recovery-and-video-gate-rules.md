# Empirical Recovery & Follow Gate Rules (Updated 2026-09-15)

## 1. Video Gate Threshold: >= 10 Videos Required
- **Quy tắc mới (15/09/2026):** Nick bắt buộc phải có **`>= 10 video` đã đăng** mới được kích hoạt tính năng follow.
- **Lý do thực nghiệm:** Nick < 10 video (đặc biệt nick mới reg, 0-4 video) có trust score rất thấp đối với Risk Engine của TikTok. Nếu cho đi follow sớm, tỷ lệ bị shadow-block / nhả follow gần như 100% và một khi đã bị dính phạt liên hoàn (`fail_streak >= 3`), tỷ lệ tự hồi phục là **0%** (liệt follow dài hạn).
- **Vị trí áp dụng đồng bộ:**
  - `tiktok-follow/follow_runner/core/follow_state.py`: `session_budget()` gate `video_count >= 10`.
  - `tiktok-follow/follow_runner/flows/follow_engine.py`: Lọc target anchor UIDs `>= 10`.
  - `tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`: Skip an toàn với log `under-10-videos-follow-disabled`.

## 2. Thống kê tỷ lệ hồi phục thực tế sau phạt nhả follow
Đối soát từ 210 account states (`follow_state_*.json`) tại farm:
- **Tỷ lệ hồi phục chung:** **12.8%** (23/179 nick từng bị phạt nhả).
- **Row 1 (Nick lâu đời, nhiều video):** Hồi phục **15.6%** (7/45 nick).
- **Row 2 (Nick trung bình):** Hồi phục **23.5%** (16/68 nick).
- **Row 3 & Row 4 (Nick mới, ít video):** Hồi phục **0%** (34/34 và 32/32 nick tiếp tục dính án phạt).

## 3. Thời gian cần để hồi phục theo Failure Streak
- **Streak = 1 (Phạt nhẹ lần đầu):** Hồi phục sau **1 – 2 ngày**. TikTok chỉ tạm khóa trong ngày. Ngày hôm sau chỉ lướt feed nhẹ, ngày thứ 2 mở lại follow bình thường.
- **Streak = 2 (Tái diễn lần 2):** Hồi phục sau **4 – 5 ngày** ngâm nghỉ kết hợp lướt feed tích trust.
- **Streak >= 3 (Shadow-ban nặng):** Bị khóa tối thiểu **7 – 10 ngày** hoặc liệt follow vĩnh viễn nếu nick yếu.

## 4. Cơ chế Post-Cooldown Warmup (Dưỡng nick sau khi hết phạt)
- **Vấn đề đã khắc phục:** Code cũ xóa sạch `fail_streak = 0` ngay ở lượt follow đầu tiên của ngày, khiến các phiên tiếp theo trong cùng ngày bị đẩy vọt lên full budget (15-20 lượt) gây tái phạt.
- **Quy tắc bảo vệ:**
  - Khi nick mãn hạn cooldown và follow thành công (`mark(STATUS_FOLLOWED)`), **KHÔNG xóa ngay `fail_streak = 0`** trong ngày.
  - Cờ `is_post_cooldown_warmup` được giữ suốt cả ngày hôm đó để giới hạn cứng budget ở mức **3 – 5 lượt/phiên**.
  - `fail_streak = 0` chỉ được reset khi sang ngày mới thông qua `_roll_day()` sau khi nick đã hoàn tất 1 ngày dưỡng an toàn.
