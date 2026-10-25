# Browser CDP Session & Form Vision Verification Guide

## 1. Bối Cảnh & Sự Cố Cần Phòng Ngừa
Khi tương tác với trình duyệt qua Remote Debugging (Chrome CDP trên cổng 9222) để kiểm tra trạng thái tài khoản hoặc xử lý các cổng dịch vụ (như GitHub, Google, Mua Sắm Công):
- **Bẫy suy đoán cảm tính**: Vừa điều hướng sang URL hoặc thấy lệnh trả về mã 200/404 đã vội vã đưa ra kết luận (ví dụ: tự ý phán "đã đăng nhập rồi" hoặc "bị chặn hoàn toàn") mà không có bằng chứng thực tế từ giao diện.
- **Bẫy gửi ảnh đối phó / gửi ảnh mù**: Lưu ảnh chụp màn hình vào đĩa rồi ném thẻ `MEDIA:` vào tin nhắn trả lời User mà không hề mở ảnh ra soi mắt kiểm tra trạng thái form hiển thị.

## 2. Quy Trình Chụp & Soi Mắt Màn Hình Trình Duyệt Qua CDP
1. **Khởi chạy & Chụp ảnh màn hình qua CDP**:
   - Sử dụng WebSocket DevTools kết nối vào trang đang active.
   - Gọi phương thức `Page.captureScreenshot` với tham số `{"format": "png"}`.
   - Giải mã dữ liệu Base64 và lưu file ảnh thực tế vào thư mục chuyên biệt (ví dụ: `D:/Taadaa/logs/screenshots/<target>_screen.png`).
2. **Kỷ luật soi mắt trước khi báo cáo (Mandatory Pre-Send Vision Audit)**:
   - BẮT BUỘC mở file ảnh bằng `browser_vision` (hoặc WinRT OCR) trước khi gửi bất kỳ kết luận nào.
   - **Kiểm tra hiện trạng Form**:
     * Ô Username / Email và ô Password đang để trống hay đã được trình duyệt autofill sẵn?
     * Có xuất hiện gợi ý đăng nhập liên kết (ví dụ: "Sign in with Google", "Sign in with a passkey", OAuth modal)?
     * Có bị dính màn hình xác thực 2 bước (2FA, OTP, số khớp điện thoại), CAPTCHA, hay lỗi Cloudflare WAF không?
   - **Xác nhận trang đích thực tế**:
     * Nếu bị redirect từ trang cài đặt (Settings / Security) về màn hình đăng nhập (`/login`), xác nhận rõ ràng lý do là phiên hiện tại chưa có cookie xác thực, tránh nhầm lẫn với lỗi 404 hay lỗi server.
3. **Phản Hồi Minh Bạch Kèm Thẻ `MEDIA:`**:
   - Trong tin nhắn trả lời User, BẮT BUỘC đính kèm thẻ `MEDIA:<path_anh_thuc_te>`.
   - Xác nhận bằng lời mô tả ngắn gọn nội dung đã thấy tận mắt qua vision (ví dụ: *"Ảnh chụp thực tế từ Chrome CDP hiển thị giao diện Sign in to GitHub, 2 trường Username và Password hoàn toàn để trống, phía dưới có nút Sign in và Sign in with a passkey, chưa có session đăng nhập"*).
   - Tuyệt đối CẤM ném link ảnh vô cảm hoặc khẳng định bừa bãi khi chưa soi mắt kiểm chứng.
