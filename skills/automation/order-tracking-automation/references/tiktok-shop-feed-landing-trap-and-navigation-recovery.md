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
1. **Fallback Vị Trí Cứng Navigation Bar & Thoát Phòng LIVE:**
   - Nếu phát hiện đang ở phòng LIVE (`Dang LIVE`, `Tin nhan`, video livestream người khác): TikTok ẩn hoàn toàn bottom bar. CẤM tap mù vào góc dưới phải (sẽ tap nhầm ô quà tặng / bình luận). BẮT BUỘC gửi `keyevent 4` (Back) hoặc tap nút `X` góc trên để thoát phòng LIVE về Feed trước.
   - Khi ở Feed thông thường: Nếu OCR không khớp chữ nào trong `PROFILE_TAB_LABELS`, dùng tọa độ tương đối góc dưới cùng bên phải `tap(width * 0.9, height * 0.97)` để ép chuyển sang tab Hồ sơ.
2. **Cấm Gửi Phím BACK Thừa Sau Khi Switch Account (Switcher Double-Back Trap):**
   - Khi tap chọn account trên bottom sheet chuyển đổi tài khoản (`m9_switcher.png`), TikTok tự động đóng switcher và reload về Feed của tài khoản mới.
   - CẤM TUYỆT ĐỐI gửi tiếp `keyevent 4` ngay sau khi tap account. Việc gửi thêm `BACK` sẽ làm văng app hoặc thoát ngược ra màn hình rác trước đó.
3. **Xử lý Màn hình Hub Đơn Hàng ("Xem tất cả >"):**
   - Khi vào "Đơn hàng của bạn" (`m9_nga_profile.png` -> `m9_hub.png`), màn hình hiển thị Hub đơn hàng chứ chưa phải danh sách chi tiết kiện hàng.
   - BẮT BUỘC bổ sung marker `Xem tất cả >` (`Xem tät cå >`, `(923, 263)`) vào `ORDER_LIST_MARKERS` hoặc tap thẳng vào `Xem tất cả >` để mở danh sách toàn bộ đơn hàng thực tế.
4. **Xử lý Khi Đang Ở Tab Cửa hàng (Shop Mall):**
   - Không cần vào Hồ sơ -> Đơn hàng nếu đang ở Cửa hàng.
   - Quét header phía trên (`y < 500`) tìm nút "Đơn hàng" (biến thể `Don hang`, `Ddn häng`) và bấm trực tiếp để vào danh sách đơn.
5. **Phát hiện Màn hình Feed để Kéo / Chuyển Ngay:**
   - Nếu phát hiện marker của feed (`LIVE`, `Chia sẻ`, `Bình luận`, `Trang chủ`, `Đề xuất`), gửi tap ngay vào vị trí tab Hồ sơ hoặc tab Cửa hàng, cấm đứng im đợi timeout.
