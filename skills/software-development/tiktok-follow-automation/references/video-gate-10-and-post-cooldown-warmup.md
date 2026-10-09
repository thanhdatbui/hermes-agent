# Quy Tắc Gate 10 Video & Cơ Chế Dưỡng Nick Sau Phạt (Post-Cooldown Warmup)

## 1. Safety Gate >= 10 Video Đã Đăng (Updated 15/09/2026)
- **Quy tắc bất biến:** Tài khoản muốn kích hoạt tính năng Follow (cả Mode 1 search và Mode 2 following list) **BẮT BUỘC phải có tối thiểu 10 video đã đăng** (`video_count >= 10`).
- **Xử lý khi < 10 video:**
  - `session_budget()` trong `follow_state.py` trả về `0`.
  - Hook follow trong `multi_machine_feed_session.py` lập tức skip an toàn với trạng thái:
    `status: "skipped"`, `reason: "under-10-videos-follow-disabled"`, `action: "skip_follow_under_10_videos"`.
  - Cấm tuyệt đối cho nick chưa đủ 10 video đi follow để tránh bị thuật toán TikTok kích hoạt cờ phạt nhả follow (`follow-release`) dài hạn.
- **Lọc Anchor UIDs nội bộ (Mode 2):**
  - Trong `follow_engine.py`, danh sách anchor UIDs dùng để đào following list cũng bắt buộc lọc chỉ chọn những nick có `row_video_counts >= 10`.

---

## 2. Cơ Chế Dưỡng Nick Sau Phạt (Post-Cooldown Warmup)
- **Trạng thái Warmup (`is_post_cooldown_warmup`):**
  - Kích hoạt khi tài khoản đã hết hạn cooldown (`follow_failed == False`) nhưng vẫn còn lưu vết chuỗi phạt trước đó (`fail_streak > 0`).
- **Ngân sách dò nhẹ (Gentle Budget):**
  - Cấp từ **3 đến 5 lượt follow/phiên** (thay vì full 15-20 lượt) để thăm dò phản ứng của thuật toán TikTok.
- **Cạm bẫy kỹ thuật sống còn (Crucial Pitfall):**
  - Khi follow thành công một nick (`mark(STATUS_FOLLOWED)`), hệ thống gỡ bỏ các cờ lỗi nhưng **CẤM reset `fail_streak = 0` ngay ở lượt đầu tiên**.
  - **Lý do:** Nếu reset về 0 ngay lập tức, cờ `is_post_cooldown_warmup` sẽ bị tắt giữa ngày, khiến các ca/phiên tiếp theo trong cùng ngày bị vọt lên full budget, làm nick bị TikTok phạt nhả lại ngay lập tức.
  - **Giải pháp chuẩn:** Giữ nguyên `fail_streak` suốt cả ngày chạy thử nghiệm. Chỉ thực hiện reset `fail_streak = 0` khi hệ thống điểm ngày mới qua `_roll_day()`, sau khi tài khoản đã hoàn thành trọn vẹn 1 ngày chạy dò an toàn.

---

## 3. Thống Kê Tỷ Lệ & Thời Gian Hồi Phục Sau Phạt Nhả Follow
- **Tỷ lệ hồi phục thực tế:**
  - Nick có video và tuổi thọ (Row 1, Row 2): Tỷ lệ hồi phục thành công đạt **15.6% – 23.5%**.
  - Nick mới / chưa đăng video (Row 3, Row 4): Tỷ lệ hồi phục gần như **0%** nếu đã bị đánh dấu nhả follow liên tục (`fail_streak >= 3`).
- **Thời gian hồi phục theo chuỗi phạt (`fail_streak`):**
  - **Streak = 1 (Phạt nhẹ lần đầu):** Cooldown 24h. Hồi phục sau **1 đến 2 ngày** nếu được nghỉ ngơi chỉ lướt feed.
  - **Streak = 2 (Phạt lần 2):** Cooldown 4 ngày. Hồi phục sau **4 đến 5 ngày**.
  - **Streak >= 3 (Shadow-ban nặng):** Cooldown 7 ngày. Hồi phục sau **7 đến 10 ngày** (cần độ trust video cao).
