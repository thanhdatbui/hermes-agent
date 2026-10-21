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

## 5. Chống URL-only False Positive & Kiểm Tra Login Form Hiển Thị
- **Lỗ hổng URL-only**: Kiểm tra `"proofs/manage" in page.url` tự nó không chứng minh phiên đã đăng nhập thành công. Nếu người dùng chưa đăng nhập, Microsoft vẫn giữ nguyên `wreply=https%3A%2F%2Faccount.live.com%2Fproofs%2Fmanage...` trên thanh địa chỉ của form đăng nhập.
- **Tiêu chuẩn kiểm tra 2 lớp**:
  1. **Thẻ quản trị thực tế (Authenticated Cards)**: Phải xuất hiện ít nhất một nội dung chỉ có sau đăng nhập: `"thay đổi mật khẩu"`, `"tuỳ chọn bảo mật"`, `"cách để chứng minh bạn là ai"`, `"additional security options"`.
  2. **Vắng bóng form đăng nhập (No Visible Login Form)**: Kiểm tra trực tiếp xem có ô nhập liệu nào đang hiển thị hay không (`is_visible()`) thay vì dùng `.count() > 0` (vì `.count() > 0` có thể bắt trúng các input ẩn hoặc modal nền):
     ```python
     has_login_form = any(
         page.locator(sel).first.is_visible(timeout=300)
         for sel in ['input[type="password"]', '#passwordEntry', '#i0118', 'input[name="passwd"]',
                     'input[type="email"]', '#usernameEntry', '#i0116']
     )
     if has_login_form:
         logged_in = False
     ```
  Nếu còn login form đang hiển thị, kết luận `logged_in` BẮT BUỘC là `False`, bất kể URL đang là gì.

## 6. Xung Đột Nhị Phân C-Extension (`greenlet._greenlet`) & Python Version Mismatch
- **Hiện tượng**: Script Playwright crash ngay tại dòng `import playwright` hoặc `from playwright.sync_api import sync_playwright` với lỗi `ImportError: cannot import name '_greenlet' from 'greenlet'`.
- **Nguyên nhân**: Quá trình chạy kế thừa biến môi trường `PYTHONPATH` từ virtualenv (ví dụ Python 3.11 của Hermes), trong khi script được gọi bằng Python hệ thống (Python 3.12). File nhị phân biên dịch sẵn `.pyd` của 3.11 không tương thích với 3.12.
- **Cách khắc phục**: Thêm bộ lọc `sys.path` ngay tại đầu file thực thi trước khi import Playwright:
  ```python
  import sys
  sys.path = [p for p in sys.path if not ("hermes" in p.lower() and "site-packages" in p.lower())]
  ```

## 7. Xử Lý Thử Thách OTP Mail Khôi Phục (`@fviainboxes.com`) & Thoát Quarantine
- **Hiện tượng**: Khi đăng nhập trên proxy mới, Microsoft hiển thị màn hình thử thách danh tính (*"Sắp hoàn thành / Almost there"*, *"Gửi mã đến ke*...@fviainboxes.com"*).
- **Cạm bẫy**: Đưa cụm từ *"xác minh email"* vào `hard_block_keywords` sẽ làm script ngắt sớm, sau 3 chu kỳ lặp lại supervisor sẽ đẩy tài khoản vào `QUARANTINE`.
- **Giải pháp**:
  1. Loại bỏ các từ khóa thử thách danh tính khỏi `hard_block_keywords`.
  2. Tra cứu email khôi phục tương ứng từ `gmail_clean_v2.xlsx`.
  3. Bấm chọn phương thức gửi mã, điền email khôi phục và bấm *Gửi mã* (`Send code`).
  4. Gọi `fetch_recovery_email_otp(rec_email, timeout_seconds=45)` từ `mail_domain_otp_helper.py` để lấy mã OTP 6–7 số.
  5. Điền mã vào các ô `#codeEntry-0..5` hoặc `#iOttText` và submit.
  6. **Xác minh hậu điều kiện OTP (OTP Postcondition Verification)**: CẤM TUYỆT ĐỐI gán cờ thành công ngay sau khi bấm submit. Bắt buộc kiểm tra chuyển hướng URL trong vòng 8-10 giây để xác nhận Microsoft đã chấp thuận OTP và rời khỏi màn hình challenge:
     ```python
     submit_btn.click()
     time.sleep(3)
     for post_i in range(8):
         post_u = page.url
         if "proofs/manage" in post_u or "account.microsoft.com" in post_u:
             logger.info(f"OTP resolved! Landed on: {post_u}")
             otp_handled = True
             break
         time.sleep(1)
     ```
  7. **Tối ưu tra cứu Excel qua In-Memory Cache**: Dùng dict `_RECOVERY_CACHE` để lưu kết quả tra cứu `(recovery_email, refresh_token, client_id)` sau lần đọc đầu tiên, tránh đọc lại file workbook lớn từ ổ đĩa trong mỗi vòng lặp tài khoản.
  8. Sau khi cập nhật code fix, bắt buộc chạy script reset danh sách `quarantine_profiles` trong state JSON của supervisor (`reset_admin_quarantine.py`) để các nick bị kẹt được chạy lại tự động.

