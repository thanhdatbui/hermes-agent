# Microsoft Hotmail / Account GPM Login Verification & Automation Pitfalls

## 1. Tránh Điều Hướng Trần (Naked `login.live.com`)
- **Vấn đề**: Điều hướng tới `https://login.live.com` trần không mang tham số đích (`wreply`). Khi đăng nhập thành công, Microsoft sẽ đưa trình duyệt qua chuỗi redirect OAuth silent 10 bước (`complete-client-signin-oauth-silent`). Nếu có bất kỳ can thiệp nào hoặc profile chứa cookie cũ, Microsoft sẽ đẩy về trang giới thiệu chưa đăng nhập: `https://account.microsoft.com/account?pageName=Account`.
- **Giải pháp chuẩn**: Luôn điều hướng tới endpoint quản trị có gắn đích rõ ràng:
  - `https://account.live.com/proofs/manage/additional` (Endpoint chuẩn của `gpm_change_hotmail_security.py`).
  - `https://outlook.live.com/mail/`.
  Microsoft sẽ tự động chuyển hướng đến form login kèm `wreply` và sau khi đăng nhập xong sẽ lưu cookie phiên đầy đủ, đổ thẳng về trang `Tuỳ chọn bảo mật bổ sung`.

## 2. Bẫy Accessibility Skip Link `a:has-text('Bỏ qua')`
- **Nguy cơ nghiêm trọng**: Mọi trang Microsoft đều có thẻ trợ năng ẩn ở đầu trang:
  ```html
  <a slot="skip-link" class="uhf-skip-link" href="#main-content-landing">Bỏ qua để tới nội dung chính</a>
  ```
- **Hậu quả**: Nếu script tìm `a:has-text('Bỏ qua')` để bỏ qua màn hình Passkey/FIDO/Authenticator, selector sẽ bắt trúng link skip này, click neo về `#main-content-landing`, làm đứt toàn bộ chuỗi redirect xác thực đang diễn ra và giam trình duyệt ở trang chưa đăng nhập.
- **Quy tắc**:
  - TUYỆT ĐỐI CẤM dùng selector chung `a:has-text('Bỏ qua')`.
  - Chỉ dùng selector đặc thù: `#fido-cancel-button`, `button#iCancel`, `a#iCancel`, `a:has-text('Bỏ qua bước này')`, `a:has-text('Skip for now')`.
  - Luôn loại trừ class skip: `:not(.uhf-skip-link):not([slot='skip-link'])`.

## 3. Chống Nhận Diện Sai Đăng Nhập (False Positive Auth Detection)
- **Trang chưa đăng nhập (Unauthenticated Promo Landing)**:
  - Text: *"Hoàn toàn miễn phí với tài khoản Microsoft"*, *"Đăng nhập để quản lý tài khoản của bạn"*.
  - Title: *"Microsoft account | Đăng nhập hoặc tạo tài khoản của bạn ngay hôm nay – Microsoft"*.
  - Footer luôn chứa cụm từ *"Bảo mật & cookie"*, *"Quyền riêng tư"*, header có chữ *"Tài khoản Microsoft"*.
  - TUYỆT ĐỐI CẤM dùng các từ đơn lẻ như `"Tài khoản Microsoft"`, `"Bảo mật"`, `"@Phản hồi"` để kết luận đã đăng nhập.
- **Trang đã đăng nhập thật (Authenticated Dashboard)**:
  - Endpoint `account.live.com/proofs/manage/additional`: Tiêu đề *"Tuỳ chọn bảo mật bổ sung"*, thẻ *"Thay đổi mật khẩu"*, *"Kiểm chứng hai bước"*, *"Cách để chứng minh bạn là ai"*.
  - Endpoint `account.microsoft.com`: Tiêu đề *"Microsoft account | Trang chủ"*, có avatar tròn chứa tên viết tắt (initials) của user.

## 4. Kỷ Luật Canary Bắt Buộc Trước Khi Báo DONE
- Mọi thay đổi code tự động hóa GPM/Hotmail BẮT BUỘC phải chạy Canary trên ít nhất 1 profile GPM thật (`done_gate.py`).
- Coordinator BẮT BUỘC soi mắt kiểm tra OCR / Vision ảnh chụp màn hình sau Canary để xác nhận màn hình đích thực sự đã đăng nhập trước khi báo cáo kết quả.
