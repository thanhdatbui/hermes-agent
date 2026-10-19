# Probation Tier 2 Session 2 Quota Exhaustion & Veteran Ceiling 40 Rules

## 1. Nâng trần Follow Veteran lên 40 (19/10/2026)
- **Thay đổi:** `core_cap` cho nhóm `veteran` (Following > 100, Video > 25, Tuổi > 180 ngày) được nâng từ **30 lên 40**.
- **Cơ chế dò trần động (+2):**
  - Khi hoàn thành cữ chạy sạch và `budget_used >= 15`: `proven_safe_ceiling = min(40, max(curr_proven, prev_used))`.
  - Trần kích hoạt kỳ tới: `active_ceiling = min(40, max(0, new_proven + 2))`.
  - Khi bị nhả: Lùi 4 nấc an toàn nhưng không thấp hơn sàn 15 (`min(40, max(0, max(15, curr_proven - 4)))`).

---

## 2. Bẫy Quota Tổng & Vận Tốc ở Phiên 2 của Probation Tier 2

### A. Hiện tượng thực tế (Audit 19/10/2026):
- Hôm nay 9 máy chạy Tier 2 (`clean_days = 1`, trần ngày 8–9 follow):
  - **M32, M36:** P1 chạy 8 follow. P2 cấp đúng `budget = 1` ➔ bấm 1 follow xong hết budget dừng ngay ➔ **Sạch 100%, tích lũy đủ 2 clean days để tốt nghiệp**.
  - **M29, M38, M39:** P1 chạy 6–7 follow sạch sẽ. P2 cấp `budget = 2` hoặc `3` để vét trần ngày ➔ **Bấm thành công người thứ nhất (+1 follow)**, nhưng đến người thứ 2 thì chạm trần Quota tổng / Rate-limit của TikTok ➔ `FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`.
  - Hậu quả: Dính án tù 3 ngày (`cooldown_until: 2026-10-22`), xóa sạch `clean_days`, mất cơ hội tốt nghiệp dù toàn bộ follow ở P1 và lượt đầu P2 TikTok vẫn giữ nguyên trên Web (+7, +8 follow).

### B. Bản chất thuật toán TikTok:
1. **Quota tổng theo tầng:**
   - Cựu binh (Graduated): Quota 30 – 40 follow/ngày.
   - Phục hồi Tier 2: Quota bị bóp nghẹt ở ngưỡng 7 – 8 follow/ngày.
   - Mới ra tù Tier 1: Quota 3 – 5 follow/ngày.
2. **Cửa sổ trượt (Sliding Velocity Window):**
   - Khoảng cách giữa P1 (06:00) và P2 (08:00) chỉ 2 tiếng, TikTok chưa reset cửa sổ đánh giá.
   - Khi P1 đã gõ 6–7 follow, sang P2 nick chỉ còn dư địa tối đa **đúng 1 lượt follow**. Cố bấm thêm lượt thứ 2 chắc chắn bị Action Block.

### C. Quy tắc bảo vệ Probation:
- Với nick đang trong diện Probation Tier 2: Nếu P1 đã chạy được $\ge 5$ follow:
  - Hoặc **dừng luôn ở P1** không cho chạy P2.
  - Hoặc nếu chạy P2 thì **bắt buộc clamp `budget = min(remaining, 1)`**, tuyệt đối không cấp `budget >= 2` ở P2.

---

## 3. Tier-Aware Circuit Breaker & Trạng thái Dashboard

- **Rule:** Cầu dao IP CHỈ giật (`trip_ip_breaker()`) khi nick CẤP KHỎE (Graduated cựu binh, `was_graduated == True`) bị nhả.
- **Nick Probation bị nhả:** Bỏ qua cầu dao IP, chỉ phạt Cooldown tầng account (3–15 ngày).
- **Ý nghĩa hiển thị:** Dashboard báo `🛡️ IP Circuit Breaker: Active 100% - Tất cả các cổng proxy đều sạch sẽ` là hoàn toàn chính xác khi các nick bị nhả đều là probation/tân binh, không phải lỗi hệ thống hay proxy.
