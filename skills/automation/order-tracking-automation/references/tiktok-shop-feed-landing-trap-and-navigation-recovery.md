# TikTok Shop Order Phase 1: Feed Landing Trap & Navigation Recovery

## 1. Hiện tượng: Kẹt Màn Hình Feed Khi Mở TikTok (Feed Landing Trap)
Khi watchdog Phase 1 (`tiktok-app-order-sync` / `order_lifecycle.py`) mở app TikTok trên điện thoại farm:
- App thường mở ra màn hình **Feed / Lướt Video / Dành cho bạn / Đề xuất** thay vì tab Profile hoặc Cửa hàng.
- WinRT OCR trên màn hình này thường nhận các biến thể chữ lệch dấu / kerning:
  * Nút Hồ sơ: `Hö sd`, `Ho so`, `Ho se`, `Profile`.
  * Nút Cửa hàng: `Cdfa hång`, `Cửa hàng`, `Shop`.
  * Nút Hộp thư: `Hép thi-f`, `Hộp thư`.
  * Nút Trang chủ: `Trang chi`, `Trang chủ`.

## 2. Bẫy Timeout 38s & Cơ chế False Negative
- Nếu logic điều hướng không nhận diện được biến thể OCR thanh navigation bar dưới đáy (`y > 1700`), vòng lặp `while time.monotonic() < deadline` (38s) sẽ cạn giờ.
- Khi cạn giờ, hàm `_capture_tracking` vẫn chụp ảnh hiện trường và lưu lại thành `order_xxx_app.jpg`.
- **Hậu quả:** Ảnh lưu lại là ảnh màn hình video TikTok/Feed. Parser không tìm thấy mã vận đơn trên video, trả về `NO_TRACKING_ON_SCREEN` và thoát trong im lặng (`silent watchdog`), khiến đơn bị kẹt mãi ở Phase 1 mà không bóc được mã.

## 3. Quy tắc Điều hướng Khắc phục Dứt điểm
1. **Fallback Vị Trí Cứng Navigation Bar:**
   - Nếu OCR không khớp chữ nào trong `PROFILE_TAB_LABELS`, bắt buộc dùng tọa độ tương đối góc dưới cùng bên phải:
     `tap(width * 0.9, height * 0.97)` để ép chuyển sang tab Hồ sơ.
2. **Xử lý Khi Đang Ở Tab Cửa hàng (Shop Mall):**
   - Không cần vào Hồ sơ -> Đơn hàng nếu đang ở Cửa hàng.
   - Quét header phía trên (`y < 500`) tìm nút "Đơn hàng" (biến thể `Don hang`, `Ddn häng`) và bấm trực tiếp để vào danh sách đơn.
3. **Phát hiện Màn hình Feed để Kéo / Chuyển Ngay:**
   - Nếu phát hiện marker của feed (`LIVE`, `Chia sẻ`, `Bình luận`, `Trang chủ`, `Đề xuất`), gửi tap ngay vào vị trí tab Hồ sơ hoặc tab Cửa hàng, cấm đứng im đợi timeout.
