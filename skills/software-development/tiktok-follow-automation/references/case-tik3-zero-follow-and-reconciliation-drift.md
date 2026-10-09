# Triệu chứng & Nguyên nhân Lệch Đối Soát Web và Tắc Nghẽn Follow Tik3 / Row 3 (2026-09-27)

## 1. Bản chất Lệch Âm vs Lệch Dương khi Đối Soát TikTok Web

### A. Lệch Âm (Script báo có follow nhưng Web server tăng ít hơn hoặc +0)
- **Silent Action Block / Drop Ngầm từ TikTok Server:**
  - Trên Android app, giao diện áp dụng **Optimistic UI**: bấm nút Follow là app lập tức đổi trạng thái sang "Đang theo dõi" trên RAM cache.
  * Khi script kiểm tra UI (in-session check), nút hiển thị đã follow -> script tính là thành công.
  * Tuy nhiên, API request gửi về server ByteDance bị rate limit hoặc flag IP proxy -> Server âm thầm drop request mà app không báo lỗi.
- **Nhả Follow Tức Thì (Instant Released):**
  * Nick vừa follow xong thì bị TikTok bot detection nhả lại ngay lập tức. Nếu runner có logic vuốt refresh kiểm tra lại ngay (như check nhả follow) thì bắt được `FOLLOW_FAILED`, nếu không bắt kịp thì sẽ phản ánh thành lệch âm trên Web scraper.

### B. Lệch Dương Ảo (Web tăng nhiều hơn Script báo)
- **Bẫy Mốc Baseline `session_start_iso` trong Watchdog:**
  - Khi chạy Phiên 2 (ví dụ 09:50), watchdog tìm snapshot trước phiên (`timestamp <= session_start_iso`). Nếu giữa phiên 1 và phiên 2 không có snapshot trung gian, watchdog sẽ lấy snapshot lúc 07:00 sáng.
  - Kết quả: Delta cào web tính gộp cả tương tác lướt feed/follow tự nhiên từ 07:00 đến 09:50 (cả 2 phiên), so sánh với số liệu follow chéo của riêng Phiên 2 -> sinh ra lệch dương ảo (+2 đến +4).
- **Follow Tự Nhiên Khi Lướt Feed:**
  - Khi nick lướt FYP / Bạn bè, có các lượt follow tự nhiên ngẫu nhiên (chạm nút + trên video). Scraper trên Web cào `followingCount` tổng hợp, không tự bóc tách được nguồn nếu watchdog không cộng gộp `cross_cnt + nat_cnt`.

---

## 2. Tắc Nghẽn Follow Trên Dàn Nick Mới / Row 3 (Tik3)

### Hiện tượng:
- Toàn bộ dàn Tik3 (Row 3, 150 nick) nhiều ngày liền không có lượt follow chéo nào thành công (`0 follow`).

### 4 Tầng Phễu Chặn Kỹ Thuật:
1. **Gate An Toàn $\ge 10$ Video (`under-10-videos-follow-disabled`):**
   - Hầu hết nick Row 3 mới lập, tiến độ up video chậm (trung bình ~4.6 video/nick).
   - ~90% nick (135/150 nick) có < 10 video -> Hệ thống khóa cứng 100% chức năng follow để chống chết nick non.
2. **Chế Độ Dưỡng Sinh (~33%):**
   - 1/3 số nick mỗi ngày rơi vào `organic-rest-day-pure-feed` (chỉ lướt feed giải trí, tắt hoàn toàn follow & upload).
3. **Bẫy Nhả Follow Ngay Tại Anchor Đầu Tiên (`FOLLOW_FAILED`):**
   - Với số ít nick đủ điều kiện ($\ge 10$ video) được thả chạy: khi vừa follow nick Anchor đầu tiên, bước verify vuốt kiểm tra phát hiện TikTok nhả đỏ ngay lập tức -> Runner kích hoạt Fail-Closed ngắt phiên khẩn cấp để cứu nick (`anchor bị nhả sau vuốt — dừng session`).
4. **Cooldown 24h Sau Khi Nhả (`follow-released-daily-cooldown`):**
   - Nick vừa bị nhả ở ca sáng sẽ bị gắn cờ cooldown 24h, tự động skip ở tất cả các ca tiếp theo trong ngày.
