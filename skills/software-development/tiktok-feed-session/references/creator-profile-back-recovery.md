# Creator Profile Drift & Back Recovery (TikTok Feed Session)

## Nguyên nhân
1. **Vuốt chéo (Swipe Left):** Cử chỉ vuốt dọc có độ lệch ngang lớn ($\Delta X$) khiến TikTok ViewPager nhận diện nhầm thành cử chỉ vuốt từ phải sang trái mở Profile của tác giả video.
2. **Tap nhầm nút/vùng avatar:** Trong luồng `_maybe_follow_video`, element `Follow` nằm sát dưới `user_avatar` hoặc username, khi tap lệch sẽ chuyển hướng vào Profile.

## Cơ chế xử lý & Recovery
- **Tự động BACK phục hồi:**
  - Bổ sung `profile` vào danh sách màn hình tự động phục hồi bằng phím `BACK` (`_back_recoverable`).
  - Trong `_recover_post_swipe_to_for_you`: Khi phát hiện màn hình là `profile` / `external_profile`, tự động gửi `KEYCODE_BACK` (keyevent 4), chờ 1.0s và định vị lại For You / Home feed để tiếp tục nuôi, tránh kích hoạt dừng phiên giữ hiện trường với lỗi `feed not confirmed`.
- **Hạn chế bấm/vuốt nhầm:**
  - Giữ trục vuốt thẳng đứng (horizontal jitter $\Delta X \le 15\text{px}$).
  - Đảm bảo tính tự nhiên bằng cách ngẫu nhiên hóa thời gian xem (dwell time: 3s–8s+), tốc độ vuốt (swipe duration: 550ms–750ms) và biên độ trục Y ($Y_{start} \approx 1540, Y_{end} \approx 620$).
