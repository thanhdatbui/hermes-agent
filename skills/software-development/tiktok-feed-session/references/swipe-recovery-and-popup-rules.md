# TikTok Feed Session Recovery & Popup Rules

## 1. Swipe Recovery on Stuck (Ưu tiên vuốt trước khi dừng)
- **Nguyên tắc:** Gặp màn hình lạ hoặc video quảng cáo không nhạy cảm (không phải Login, OTP, Captcha, Password, Security Check) tại bất kỳ phase nào:
  - Phase `baseline` (vừa khởi động app)
  - Phase `before_swipe` (sau khi bấm Home)
  - Phase `swipe_after` (trong vòng lặp lướt video)
- **Thực thi:** PHẢI kích hoạt `_swipe_recovery_on_stuck` (vuốt thử 2 lần) TRƯỚC `manual_guard` và trước khi gọi `finalize_feed_session_cleanup` / báo lỗi dừng giữ hiện trường.

## 2. Xử lý Popup / Màn hình "Follow bạn bè" / "Follow lại"
- Khi gặp modal hoặc tab chuyển hướng sang danh sách gợi ý "Follow bạn bè của bạn" / "Follow lại":
  - Bấm ngẫu nhiên tối đa 1 đến 2 nút "Follow lại" (hoặc "Follow back").
  - Sau đó điều hướng bấm về tab "Đề xuất" (For You) / "Trang chủ" hoặc bấm nút đóng (X) / Back để khôi phục về feed chính và tiếp tục phiên nuôi acc.
