# IME Keyboard / Input Composer Overlay & Swipe Recovery Trap

## Tình huống & Triệu chứng
1. Màn hình TikTok rơi vào trạng thái mở bàn phím ảo (Samsung/AOSP IME) kèm thanh nhập liệu (Comment / Story Quick Reply / Chat bar).
2. Bàn phím chiếm nửa dưới màn hình (`y ≈ 950` đến `y = 1920`), che hoàn toàn thanh điều hướng đáy (*Trang chủ*, *Hồ sơ*).
3. `core/classifier.py` không tìm thấy các marker chuẩn của Feed/Bottom Bar nên phân loại màn hình là `unknown` $\rightarrow$ `safety.py` kích hoạt `unknown TikTok state`.
4. Runner kích hoạt cứu nguy `_swipe_recovery_on_stuck` với tọa độ swipe `(540, 1600) -> (540, 400)`. Điểm xuất phát `y=1600` rơi trúng vùng bàn phím ảo, thao tác swipe vào bàn phím không có tác dụng cuộn Feed và không tắt được bàn phím/composer bar.
5. Sau 2 lần swipe không thay đổi trạng thái, runner kết luận `swipe recovery (2 swipes) still stuck` và dừng phiên.

## Quy tắc Xử lý & Khắc phục
1. **Khử bàn phím trước khi Swipe Recovery:**
   - Trong `_swipe_recovery_on_stuck`, trước khi thực hiện các cú swipe cứu nguy, bắt buộc phải kiểm tra và hạ bàn phím ảo (`input keyevent BACK` hoặc `input keyevent 111` / Escape) nếu IME đang hiển thị.
   - Tọa độ swipe fallback phải đảm bảo bắt đầu ở nửa trên màn hình (`y < 900`) để không bị nuốt bởi overlay / keyboard.
2. **Đăng ký Benign Popup / Input Overlay vào `BENIGN_POPUP_REGISTRY`:**
   - Nhận diện `EditText` đang focused kèm IME hoặc nút gửi comment/tin nhắn là benign popup cần dismiss.
   - Hàm dismiss gửi phím `BACK` để hạ bàn phím và đóng composer về lại Feed chính.
