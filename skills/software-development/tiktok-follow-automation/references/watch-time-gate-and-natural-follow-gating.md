# Watch Time Gate & Phân Tách Cổng Follow (Natural vs Cross-Repo)

## 1. Bản chất hiện tượng TikTok "Nhả Follow" (Silent Follow Drop)
- **Hiện tượng:** Bot bấm nút Follow trên UI thành công (nút chuyển sang Đang follow/Bạn bè), nhưng sau vài giây hoặc khi reload, TikTok âm thầm revert lại trạng thái chưa follow.
- **Nguyên nhân cốt lõi:**
  1. **Thiếu Dwell Time / Watch Time:** Khi bot vừa quẹt tới video, chỉ dừng 1-3 giây đã bấm follow ngay ➔ AI Anti-Spam của TikTok đánh giá là bot tự động bấm dạo ➔ Drop action gửi lên server.
  2. **Account Sandbox:** Tài khoản mới chưa có đủ lịch sử xem (Watch History) trên thiết bị.

## 2. Giải pháp Watch Time Gate (Chống Nhả Follow)
Trong luồng lướt Feed tự nhiên (`_maybe_follow_video` trong `feed_swipe_smoke.py`):
- Khi roll trúng tỷ lệ follow tự nhiên (5% trên For You, 20% trên Deep Inspect), **BẮT BUỘC chèn Watch Time Gate**:
  ```python
  # Ngâm video tối thiểu 8.0s - 12.0s trước khi tap follow
  watch_dwell_s = random.uniform(8.0, 12.0)
  time.sleep(watch_dwell_s)
  ```
- Việc xem đủ lâu (≥ 8s) khiến thuật toán TikTok ghi nhận đây là hành vi người dùng thật thưởng thức nội dung, đảm bảo follow bám dính 100%.

## 3. Phân Tách 2 Tầng Cổng Kiểm Tra (Gating Architecture)

| Tiêu chí | Cổng 1: Follow Chéo Nội Bộ (Cross-Repo Follow Hook) | Cổng 2: Follow Tự Nhiên Khi Lướt Feed (In-Feed Natural Follow) |
| :--- | :--- | :--- |
| **Vị trí code** | `multi_machine_feed_session.py` (cuối session) | `feed_swipe_smoke.py` (trong vòng lặp swipe) |
| **Cổng chặn** | `video_count >= 10` (Nick phải đăng ≥10 video mới được mở follow nội bộ) | **KHÔNG áp dụng cổng 10 video** (Mọi nick ngâm đủ 7 ngày đều được follow tự nhiên) |
| **Cơ chế bảo vệ** | Tránh nick clone chưa có video đi tương tác lộ cụm farm | **Watch Time Gate (8-12s)** + Tỷ lệ tự nhiên 5% - 20% (1-2 lượt/session) |
| **Báo cáo Telemetry** | Báo cáo qua `follow_result.json` (Module 1 / Module 2) | Báo cáo qua `summary.txt` (`follow_counts`) ➔ Hiển thị dòng `Follow tự nhiên` trên Telegram |
