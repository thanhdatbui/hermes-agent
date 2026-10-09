# Đối soát lệch do Follow tự nhiên & Tác động của Safety Gates tới sản lượng Follow

## 1. Bản chất lệch đối soát TikTok Web (-1 / lệch số) do Natural Follow
- **Hiện tượng:** Báo cáo Watchdog ghi nhận: `M72 (@caotrinh16022004): script báo 1 | web tăng +0 (Lệch -1)`.
- **Nguyên nhân cốt lõi:**
  1. Trong phiên lướt feed (Run Row), nick thực hiện follow tự nhiên trong feed bạn bè (`natural_follows: {"friends": 1}`). Follow chéo nội bộ (Mode 2) = 0.
  2. Watchdog tính tổng số lượt báo cáo: `rep_cnt = cross_cnt + nat_cnt = 0 + 1 = 1`.
  3. Khi đối soát với `snapshots` trong `tiktok_tracker.db`:
     - Baseline snapshot (07:16): `following = 72`.
     - Post-session snapshot (07:51 / 11:11): `following = 72`.
     - Delta web = $72 - 72 = 0$.
     - Diff = $0 - 1 = -1$ (Lệch -1).
  4. Lượt follow tự nhiên trên feed TikTok không qua xác minh 2 chiều như Mode 2 (không pull-to-refresh phá cache ngay lập tức) hoặc server TikTok nuốt/nhả ngầm follow tự nhiên, hoặc cache web của TikTok chưa cập nhật kịp trước khi tracker cào snapshot.
- **Quy tắc & Giải pháp đối soát:**
  - Không được gộp mù quáng `natural_follows` vào đối soát strict mà không gắn nhãn nguồn gốc.
  - Phải tách rõ trong báo cáo đối soát: `Follow chéo (đã đối soát 2 chiều)` vs `Follow tự nhiên trên feed (unverified web cache)`.
  - Nếu có follow tự nhiên mà web delta = 0, cần retry snapshot sau 5–10 phút trước khi kết luận lệch.

## 2. Vì sao cả phiên toàn farm chỉ chạy vài máy follow?
- **Hiện tượng:** Cả cụm 80 máy chỉ có 3–4 máy thực sự kích hoạt follow.
- **Nguyên nhân (Multi-tier Safety Gating):**
  1. **Organic Rest Gate (~33%):** ~22 máy được chỉ định nghỉ ngơi (chỉ lướt feed, tắt 100% follow/up video).
  2. **Video Count Gate (< 10 videos):** 11–21 máy chưa đủ 10 video đăng trên nick đang chạy → bị chặn follow tự động.
  3. **Identity / Switcher Gate (`sensitive-skip-manual_needed`):** 35–42 máy bị lệch nick trên app (`profile username still mismatched after switch`) hoặc kẹt modal switcher → bot lập tức từ chối chạy follow hook để bảo vệ nick.
  4. **Anti-Release Cooldown Gate:** Các máy vừa bấm follow anchor đầu tiên mà bị TikTok nhả liền (`FOLLOW_FAILED`) sẽ lập tức dừng và bật cooldown `follow-released-daily-cooldown` cho cả ngày hôm đó.
- **Kết luận vận hành:** Số lượng máy chạy follow thấp trong phiên là kết quả hợp lệ của hệ thống tự vệ nhiều tầng nhằm bảo vệ tài sản nick, không phải do script bị crash hay treo.
