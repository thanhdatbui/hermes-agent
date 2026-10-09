# Dual Gate 30d/10v & Phân Tích Lịch Sử Nhả Follow (Empirical Audit 2026-10-06)

## 1. Bản Nâng Cấp Dual Gate (2026-10-06)
- **Gate cũ (2026-09-25):** `account_age_days >= 21` VÀ `video_count >= 6`.
  - Hậu quả thực tế: 182 / 185 lượt quyết định (98.4%) cho nhóm nick non (tuổi 21-30 hoặc video 6-9) đi follow mồi (3-5 budget) **bị nhả follow ngay lập tức**, rơi vào bẫy Cooldown mãn tính (streak leo lên 3-5).
- **Gate mới (2026-10-06):**
  - **Điều kiện đi follow cứng:** `account_age_days >= 30` VÀ `video_count >= 10`.
  - Thiếu bất kỳ điều kiện nào -> `budget = 0` (chặn tuyệt đối, chỉ cho dưỡng feed và đăng video).
  - `post_cooldown_warmup` (vừa mãn hạn cooldown): cấp budget thăm dò 3-5.
  - Trưởng thành (`age >= 30` & `video >= 10` & không cooldown): cấp full budget 10-20/phiên (tối đa 40/ngày).

---

## 2. Phát Hiện Thực Nghiệm: Cơ Chế Nhả Follow Của TikTok

### A. Tỷ lệ bị nhả theo tầng nick (Row / Slot)
- **Row 1:** 67/80 nick từng bị nhả (84%), nhưng có **13-15 nick sạch hoàn toàn** (never failed).
- **Row 2:** 74/78 bị nhả (95%).
- **Row 3:** 69/73 bị nhả (95%).
- **Row 4 - Row 8:** **97% - 100% bị nhả**. 287 nick ở các row dưới có tổng follow $\le 5$ (phần lớn là 0).

### B. Bản chất kỹ thuật của việc "Nhả Follow" (Silent Drop)
- Client TikTok có cơ chế **Optimistic UI**: Khi bấm Follow, nút đổi sang "Đang follow" ngay trên màn hình thiết bị.
- Nhưng ở phía backend, TikTok đánh giá **Account Trust Score**:
  - Với nick non (dưới 10 video, ít lịch sử xem feed): TikTok **silent drop** gói tin tại server gateway.
  - Khi script thực hiện **Path B verification** (re-entry profile hoặc reload danh sách followers), nút vẫn là "Follow" -> script phát hiện `not_followed` và set cờ `follow_failed = True`.

### C. Nick già dính án có bị "ngọng" vĩnh viễn không?
- **Không.** Nick già (Row 1/2, >25 video, >200 ngày tuổi) sau khi hết hạn Cooldown (3-5 ngày) vẫn quay lại cày sản lượng lớn:
  - M51 R1: Từng dính án, sau đó ăn 30-32 follow/ngày, tổng tích lũy đạt 291 follow.
  - M36 R1: Sau cooldown cày 18-43 follow/ngày, tổng đạt 222 follow.
  - M43 R1: Sau cooldown cày liên tục 6 ngày không nhả, tổng đạt 176 follow.
- **Quy luật sinh tồn:** TikTok không có miễn nhiễm vĩnh viễn. Cả nick người thật nếu follow dồn dập cũng bị dính Rolling Rate-Limit tạm thời.
  - **Chu kỳ lành mạnh của nick già:** Cày 3-5 ngày $\rightarrow$ Chạm ngưỡng rolling limit $\rightarrow$ Nghỉ Cooldown 3 ngày $\rightarrow$ Ra cày tiếp.
  - **Vòng lặp độc hại của nick non:** Không đủ 10 video mà thả ra $\rightarrow$ Bấm 1 phát dính án $\rightarrow$ Cooldown 3-5-7 ngày $\rightarrow$ Mãn hạn bấm lại dính tiếp. (Đã được chặn đứng bằng Gate 30d/10v).
