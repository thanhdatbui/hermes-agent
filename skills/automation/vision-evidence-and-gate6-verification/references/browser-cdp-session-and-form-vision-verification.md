# Browser CDP Session & Form Vision Verification Guide

## 1. Bối Cảnh & Sự Cố Cần Phòng Ngừa
Khi tương tác với trình duyệt qua Remote Debugging (Chrome CDP trên cổng 9222/cổng GPM) để kiểm tra trạng thái tài khoản hoặc xử lý các cổng dịch vụ (Facebook, Meta SSO, GitHub, Google, Mua Sắm Công):
- **Bẫy suy đoán cảm tính**: Vừa điều hướng sang URL hoặc thấy lệnh trả về mã 200/404 đã vội vã đưa ra kết luận (ví dụ: tự ý phán "đã đăng nhập rồi" hoặc "bị chặn hoàn toàn") mà không có bằng chứng thực tế từ giao diện.
- **Bẫy gửi ảnh đối phó / gửi ảnh mù**: Lưu ảnh chụp màn hình vào đĩa rồi ném thẻ `MEDIA:` vào tin nhắn trả lời User mà không hề mở ảnh ra soi mắt kiểm tra trạng thái form hiển thị.
- **Bẫy chụp lệch pha (State Mismatch / Race Condition)** (Sự cố 2026-10-30):
  * Agent báo cáo tài khoản bị chặn / sai mật khẩu / đòi SMS 2FA, nhưng ảnh đính kèm gửi User lại chụp trước khi submit hoặc khi form đang rỗng / còn nguyên ở ô mật khẩu chưa nộp.
  * Hậu quả: User phản ứng gay gắt vì ảnh gửi không khớp với lời khẳng định (*"Hình mày chụp vẫn đang ở ô nhập mật khẩu chả có chỗ nào nó ép nhận sms cả"*).

## 2. Quy Trình Chụp & Soi Mắt Màn Hình Trình Duyệt Qua CDP
1. **Khởi chạy & Chụp ảnh màn hình qua CDP**:
   - Sử dụng WebSocket DevTools kết nối vào trang đang active.
   - Gọi phương thức `Page.captureScreenshot` hoặc Playwright `page.screenshot()`.
   - Lưu file ảnh thực tế vào thư mục chuyên biệt (ví dụ: `D:/Taadaa/logs/screenshots/<target>_screen.png`).

2. **Kỷ luật chụp đúng thời điểm (Pre & Post Action Checkpoints)**:
   - **Checkpoint 1 (Pre-Submit)**: Chụp ngay sau khi điền xong Username + Password để chứng minh dữ liệu đã nằm trên form.
   - **Thao tác Submit đáng tin cậy**: Trên giao diện React / Next.js (như Facebook / Meta), nút click dễ bị nuốt sự kiện (event swallowing). Luôn ưu tiên `locator.press('Enter')` trong ô password hoặc `requestSubmit()`.
   - **Checkpoint 2 (Post-Submit / Settled State)**:
     * BẮT BUỘC chờ đợi trạng thái ổn định (Navigation kết thúc, URL đổi, hoặc xuất hiện banner thông báo lỗi như `[role="alert"]`, chữ *"Bạn đã nhập sai thông tin đăng nhập"*).
     * Tuyệt đối KHÔNG chụp khi form vừa reset trắng mà chưa kịp hiển thị banner lỗi, hoặc khi trang chưa kịp load xong.

3. **Kỷ luật soi mắt trước khi báo cáo (Mandatory Pre-Send Vision Audit)**:
   - BẮT BUỘC mở file ảnh bằng `browser_vision` (hoặc WinRT OCR) trước khi gửi bất kỳ kết luận nào.
   - **Kiểm tra hiện trạng Form**:
     * Ô Username / Email và ô Password đang để trống hay đã được trình duyệt autofill sẵn?
     * Có xuất hiện thông báo lỗi cụ thể (banner đỏ, viền đỏ, popup `Invalid request`) không?
     * Có bị dính màn hình xác thực 2 bước (WhatsApp / SMS / Authenticator app), CAPTCHA (reCAPTCHA v2 / Enterprise) không?
   - **Xác nhận trang đích thực tế**:
     * Nếu bị redirect từ trang cài đặt về màn hình đăng nhập (`/login`), xác nhận rõ ràng lý do là phiên hiện tại chưa có cookie xác thực, tránh nhầm lẫn với lỗi 404 hay lỗi server.

4. **Phản Hồi Minh Bạch Kèm Thẻ `MEDIA:`**:
   - Trong tin nhắn trả lời User, BẮT BUỘC đính kèm thẻ `MEDIA:<path_anh_thuc_te>`.
   - Xác nhận bằng lời mô tả ngắn gọn nội dung đã thấy tận mắt qua vision (ví dụ: *"Ảnh chụp thực tế từ Chrome CDP hiển thị khung cảnh báo đỏ 'Bạn đã nhập sai thông tin đăng nhập' ngay dưới tiêu đề Đăng nhập vào Facebook"*).
   - Tuyệt đối CẤM ném link ảnh vô cảm hoặc khẳng định bừa bãi khi chưa soi mắt kiểm chứng.
