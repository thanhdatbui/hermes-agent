# Browser Automation & Gate 6 Visual Evidence Checklist: Form Submit Verification

## 1. Bản Chất Sự Cố
Trong các phiên tự động hóa trình duyệt (CDP, Playwright, GPM, Puppeteer) thao tác trên các form đăng nhập hoặc xác thực phức tạp (Meta/Facebook/Instagram, Google, TikTok):
- **Bẫy "Tưởng Đã Gửi Nhưng Chưa Nộp" (Unsubmitted Form Trap):** Agent dùng lệnh click chuột hoặc script JS nộp form, nhưng form không chuyển trang hoặc sự kiện bị nuốt (React event listener chưa kích hoạt, hoặc click nhầm coordinate/element container). Ảnh chụp sau đó vẫn đứng nguyên tại form nhập mật khẩu chưa có phản hồi lỗi thực sự từ server.
- **Phản ứng của User:** User nhìn vào ảnh thấy ô mật khẩu vẫn hiển thị bình thường, không có lỗi hay thông báo gì -> Phản ánh trực tiếp: *"Hình đâu"*, *"Hình mày chụp vẫn đang ở ô nhập mật khẩu"*, *"Chả có chỗ nào nó ép nhận SMS cả"*.

---

## 2. Kỷ Luật Xác Minh Trước - Sau (Atomic Pre/Post Submit Verification)
Khi thực hiện nộp form trên web UI:

1. **Pre-submit Capture (Checkpoint 1):**
   - Đảm bảo các trường đã được điền text/pass hoàn chỉnh.
   - Chụp ảnh xác nhận dữ liệu đã nằm trên input.

2. **Trigger Nộp Form Đáng Tin Cậy:**
   - Ưu tiên focus vào ô password và dùng `press('Enter')` để kích hoạt sự kiện submit native của trình duyệt thay vì chỉ mouse click vào tọa độ (mouse click tọa độ dễ lệch hoặc bị nuốt).
   - Kiểm tra `page.url` và DOM change liên tục trong 1-5 giây để xác nhận form đã thực sự được gửi đi.

3. **Post-submit Capture (Checkpoint 2 - BẮT BUỘC CÓ KẾT QUẢ PHẢN HỒI):**
   - TUYỆT ĐỐI KHÔNG chụp ảnh nghiệm thu khi form vừa bị click nhưng trang chưa hề tải xong hoặc chưa có thông báo phản hồi từ server.
   - Bắt buộc chờ phản hồi rõ ràng:
     - URL thay đổi (chuyển sang checkpoint, 2fa, dashboard), HOẶC
     - Có thông báo lỗi cụ thể (khung màu đỏ, alert banner như *"Bạn đã nhập sai thông tin đăng nhập"*, *"Tài khoản không tồn tại"*).
   - Nếu chụp ảnh mà trên form vẫn chỉ là ô nhập rỗng hoặc giữ nguyên trạng thái cũ mà không có thông báo lỗi -> BẮT BUỘC coi là hành động submit chưa hoàn thành, cấm vội kết luận hay giải thích khi ảnh chưa có bằng chứng hiển thị.

---

## 3. Khắc Phục Lỗi "Silent Form Reset"
- Khi Facebook/Meta xóa trắng cả 2 ô input sau khi submit qua proxy: Đây là cơ chế tự bảo vệ khi client script submit không hợp lệ (click event bị nuốt hoặc captcha/fingerprint bị chặn). Cần kích hoạt bằng phím `Enter` trực tiếp trên ô input mật khẩu (`pass_box.press('Enter')`).
- **Phân biệt rạch ròi giữa Form Đăng Nhập vs Form Khôi Phục (Recovery):**
  - Form Đăng nhập chính (`/login`): Khi điền pass sai, hệ thống báo đỏ trực tiếp: *"Bạn đã nhập sai thông tin đăng nhập"*.
  - Form Khôi phục (`/recover/initiate`): Luôn hiện các phương thức nhận mã OTP (SMS/WhatsApp). KHÔNG ĐƯỢC dùng màn hình Recovery để suy diễn rằng form đăng nhập chính bị ép nhận SMS khi bản thân mật khẩu nhập vào chưa từng được xác nhận đúng.
- Soi mắt bằng vision trước khi gửi ảnh: BẮT BUỘC xác nhận rõ ràng trong ảnh có banner cảnh báo lỗi cụ thể trước khi kết luận và giải thích cho User.
