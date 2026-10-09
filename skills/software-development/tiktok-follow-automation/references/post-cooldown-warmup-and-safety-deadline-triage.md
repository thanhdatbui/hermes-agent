# Post-Cooldown Warmup & Safety Deadline Triage (2026-09-16)

## 1. Cơ chế Warm-up sau Cooldown (Nick mãn hạn phạt)
- **Thuộc tính phát hiện:** `is_post_cooldown_warmup` (`fail_streak > 0` và `not follow_failed`).
- **Ngân sách tự động bóp nhỏ:** Trong `follow_state.py:session_budget()`, thay vì cấp full quota `10-20` follow/phiên, hệ thống tự động bóp quota xuống `3 - 5` follow (`random.randint(3, 5)`).
- **Hiện tượng báo cáo:** Watchdog ghi nhận máy chạy thành công `1 - 4 lượt` (hoặc `5 lượt`) với trạng thái `OK` thay vì 10-20 lượt.
- **Quy tắc chẩn đoán:**
  - Nếu `status == "OK"` và `follow_failed == False`: KHÔNG PHẢI BỊ NHẢ. Đây là do nick chạm trần ngân sách warm-up an toàn hoặc cạn UID chưa follow trong list Anchor.
  - Sau khi hoàn thành phiên warm-up này, `state.mark()` sẽ reset `fail_streak = 0` để các cữ sau quay lại quota bình thường.

## 2. Safety Deadline Gate (Mode 2 -> Mode 1)
- **Ngưỡng an toàn reserve:** `has_time_for_next_action(reserve_seconds=180.0)` trong `follow_engine.py`.
- Khi Mode 2 đã ngốn gần hết `feed_timeout_seconds` (thường là 1200s, thời gian còn lại < 180s):
  - Script chủ động log: `Session deadline approaching, skipping mode1 after mode2 with N followed accounts`.
  - Kết thúc session an toàn với `status: "OK"` mà KHÔNG chuyển sang Mode 1 Search UID để tránh rủi ro watchdog trảm tiến trình giữa chừng làm kẹt màn hình TikTok.

## 3. Lịch toán học Chẵn / Lẻ vs Ngày Dưỡng Sinh (Modulo 6)
- **Lịch phân Row:** 
  - Ngày Chẵn (`date % 2 == 0`): 100% farm chạy Row 2, 4, 6, 8.
  - Ngày Lẻ (`date % 2 == 1`): 100% farm chạy Row 1, 3, 5, 7.
  - KHÔNG pick ngẫu nhiên dãy nick.
- **Ngày Dưỡng sinh (Modulo 6):**
  - Áp dụng chu kỳ 6 ngày: Day 0, 4 (Lẻ) & Day 1, 3 (Chẵn) là ngày cày. Day 2, 5 là ngày Dưỡng sinh.
  - Trong ngày Dưỡng sinh, farm vẫn chạy đúng dãy Row của ngày hôm đó, nhưng tắt tính năng follow (`budget = 0`) và upload để tài khoản nghỉ ngơi giữ trust.
