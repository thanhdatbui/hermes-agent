# Quy tắc Vận hành Follow Hook, Timeout Isolation & Kiểm tra Nhả Follow (2026-08-26)

## 1. Bối cảnh & Chu trình Pipeline Ca / Phiên Chuẩn
- **Mỗi phiên thường (Phiên 1 & 2 trong ca):**
  - Chạy tuần tự: **Nuôi Feed (Fast Swipe + Deep Inspect) ➔ Follow Hook (`tiktok-follow`)**.
- **Phiên cuối ca (Phiên 3):**
  - Chạy đủ 3 bước: **Nuôi Feed ➔ Follow Hook (`tiktok-follow`) ➔ Upload Video**.
- **Phân định 2 nguồn Follow:**
  - *Follow tự nhiên (Organic):* 20% tại nhịp Deep Inspect tab For You (~0.7 follow/phiên, ~2-3 follow/ca/ngày).
  - *Follow chéo (`tiktok-follow`):* Kích hoạt qua subprocess sau feed, theo Gate Video (0 video = 0 fl; 1-5 video = 3-5 fl; >5 video = 6-10 fl).

## 2. Kiến trúc Timeout Isolation Độc lập (Multi-Tier Timeout)
- **Feed Session:** Cấp riêng 2100s (~35 phút).
- **Follow Hook:** Cấp riêng 900s (15 phút), chạy subprocess độc lập.
- **Upload Hook:** Cấp riêng 1200s (20 phút), chạy subprocess độc lập.
- **Outer Watchdog Safe Hard Timeout:**
  $$\text{Safe Timeout} = \text{Feed (2100s)} + \text{Follow (900s)} + \text{Upload (1200s nếu phiên 3)} + \text{Buffer (300s)}$$
  - Phiên 1 & 2: 3300s (~55 phút).
  - Phiên 3: 4500s (~75 phút).
  - Đảm bảo follow và upload chạy không bao giờ làm cạn timeout của phiên nuôi feed.

## 3. Quy trình Xác thực Nhả Follow (Pull-to-refresh) & Kết quả Kiểm tra 26/08
- Sau khi bấm nút Follow thành công trên Profile:
  1. Thực hiện thao tác vuốt kéo từ trên xuống (*Pull-to-refresh*, $y_1 = 35\%h \rightarrow y_2 = 80\%h$, `duration_ms=500`) qua hàm `pull_to_refresh_profile()` để kích hoạt thanh loading reload profile của TikTok.
  2. Bắt buộc kiểm tra lại trạng thái nút Action:
     - Nếu nút vẫn giữ trạng thái *"Nhắn tin"* / *"Đã follow"* $\rightarrow$ Xác nhận thành công thật sự (`FOLLOW_SUCCESS`).
     - Nếu nút bị nhảy ngược về *"Follow"* (màu đỏ) $\rightarrow$ Đánh dấu `FOLLOW_FAILED` (TikTok chặn follow/nhả follow).
- **Xử lý sự cố khi dính `FOLLOW_FAILED`:**
  - Dừng ngay lập tức phiên follow của máy đó để bảo vệ thiết bị.
  - Ghi nhận `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"` vào file state riêng của nick (`follow_state_<máy>_row_<index>.json`).
  - Nick đó sẽ tự động bị bỏ qua (chỉ nuôi feed, không follow) trong toàn bộ các phiên còn lại của ngày hôm đó, và tự động phục hồi vào ngày hôm sau.
- **Thực tế ngày 2026-08-26:**
  - Ghi nhận **24 nick trên Row 2** bị dính cờ nhả follow (5 máy được 1-2 follow rồi nhả; 19 máy nhả ngay lượt đầu).
  - Toàn bộ Row 1 và Row 3..6 không dính cờ, vẫn hoạt động bình thường nhờ cơ chế cô lập trạng thái theo `account_row_index`.
