# TikTok Feed: Xử lý post Photo Mode (Ảnh) & Lỗi "screen capture invalid; feed not confirmed"

## Hiện tượng & Dấu hiệu nhận diện
Khi bot lướt feed TikTok gặp các post định dạng **Photo Mode (Album ảnh)**:
- Nút hoặc tag camera mang nhãn **"Ảnh"**.
- Nút chia sẻ/đăng lại: **"Đăng lại cho follower"** (Repost).
- Action bar (cột tương tác bên phải):
  - Nút comment hiển thị text placeholder **"Bóc tem"** (thay vì số lượng comment khi bài chưa có ai bình luận).
  - Icon Tim (like), Bookmark (lưu), Chia sẻ, Đĩa nhạc.
- Nền ảnh tĩnh nhiều chi tiết hoặc màu sáng có thể làm giảm confidence của visual line-detector khi xác định gạch chân tab "Đề xuất" (For You) hoặc highlight tab "Trang chủ" (Home).

## Nguyên nhân lỗi `screen capture invalid; feed not confirmed`
1. Tại `feed_swipe_smoke.py`:
   - Hàm `_is_feed_confirmed()` yêu cầu `detected_screen` nằm trong `FEED_SCREENS` (`{"home", "for-you", "sponsored"}`) hoặc `home_selected` / `for_you_selected` / `image_selected_top_tab == "for-you"`.
   - Nếu screenshot detection bị drop confidence hoặc XML dump chậm / có text lạ dẫn đến `detected_screen == "unknown"`, hệ thống ném `SCREEN_CAPTURE_INVALID_REASON = "screen capture invalid; feed not confirmed"`.
2. Khắc phục:
   - Trong `_is_feed_confirmed()` hoặc parser UI (`calibrate_screens.py` / `benign_popup.py`), bổ sung nhận diện các marker đặc trưng của feed photo post:
     - `Bóc tem`
     - `Đăng lại cho follower`
     - Text/nhãn `Ảnh` kết hợp với bottom navigation bar `Trang chủ`.
   - Khi phát hiện các marker này, khẳng định đây là feed hợp lệ (`for-you`), tránh kích hoạt retry capture ladder hoặc làm hỏng session.
