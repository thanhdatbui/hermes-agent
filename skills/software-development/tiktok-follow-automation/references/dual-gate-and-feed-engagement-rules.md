# Dual Gate Follow & Feed Engagement Architecture (2026-09-25)

## 1. Dual Gate Follow Rules (Ngày tuổi $\ge 21$ & Video $\ge 6$)
Thay thế cho Gate cứng "10 video" cũ để rút ngắn thời gian vốn chết ngâm nick:

- **Điều kiện đi follow:**
  $$\text{Được phép Follow} \iff (\text{Ngày tuổi} \ge 21\text{ ngày}) \;\mathbf{VÀ}\; (\text{Video Đã Đăng} \ge 6\text{ video})$$

- **Phân tầng Budget phiên (`session_budget` trong `follow_state.py`):**
  1. `< 21 ngày` HOẶC `< 6 video`: `Budget = 0` (chỉ lướt feed + like/bookmark dưỡng sinh, không follow).
  2. `21 – 30 ngày` VÀ $\ge 6$ video (hoặc $> 30$ ngày nhưng $6 - 9$ video): `Budget mồi = 3 – 5 follow / phiên`.
  3. `> 30 ngày` VÀ $\ge 10$ video: `Full Budget = 10 – 20 follow / phiên` (theo config máy).
  4. **Tương thích ngược:** Nick không có cột ngày tạo trong workbook nhưng có $\ge 10$ video vẫn cấp Full Budget bình thường.

### Cạm bẫy đồng bộ 3 tầng (Multi-layer Synchronization Trap)
Khi nâng cấp logic Dual Gate trong `follow_state.py`, bắt buộc phải đồng bộ xuyên suốt 3 tầng:
1. **Tầng Safe Workbook (`taikhoan_run_safe.xlsx`):** Bắt buộc sync cột 5 `Ngày Tạo` qua `sync-safe-workbook.py`.
2. **Tầng Parent Feed Hook (`multi_machine_feed_session.py`):** Gỡ bỏ chốt chặn cứng `if video_count < 10` trước khi gọi subprocess `run_follow.py` để không bị short-circuit nhầm `under-10-videos-follow-disabled`.
3. **Tầng Watchdog Báo Cáo (`feed_session_watchdog.py`):** Cập nhật bộ phân loại lý do bỏ qua từ `"Chưa đủ 10 video"` thành `"Chưa đủ điều kiện (Tuổi < 21d hoặc Video < 6)"`.

---

## 2. Anchor Pre-Engagement Flow (Mode 2)
Trong `mode2_follow_followers.py` (`_ensure_anchor_followed`):
1. Vào Profile Anchor $\to$ Tìm cover video đầu tiên.
2. Tap mở video $\to$ Dừng xem ngẫu nhiên 8 – 15 giây (`dwell = random.uniform(8.0, 15.0)`).
3. Thả tim ngẫu nhiên tỷ lệ 50% – 70%.
4. Bấm nút Follow trực tiếp trên màn hình video (avatar `+` đỏ hoặc content-desc Follow).
5. Đợi 2–4s $\to$ Back về Profile Anchor $\to$ Vuốt reload (pull-to-refresh) kiểm tra xem có bị nhả follow hay không trước khi mở tab Following.

---

## 3. Bookmark / Favorite Matrix khi Lướt Feed
Trong `feed_swipe_smoke.py`:
- **Tầng 1 (Cùng nhịp Thả tim):** Khi video được Like thành công $\to$ tỷ lệ 15% – 30% tap nút Lưu/Bookmark bên phải.
- **Tầng 2 (Lưu độc lập - `_maybe_independent_bookmark`):** Ở video không like $\to$ tỷ lệ 3% – 5% tap Lưu độc lập nhằm phá vỡ tương quan cứng Like $\to$ Save, tạo pattern tự nhiên cho nick.
