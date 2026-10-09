# Google Challenge: Xác nhận Số điện thoại (SĐT đuôi 24 - Tad) & Phân tách ô OTP

## 1. Bản chất Challenge Google Identity Verification
Khi đăng nhập Google OAuth trên GPM profile, ngoài Google Prompt (Galaxy S7) và mã bảo mật 10 số (OOTP), Google có thể kích hoạt cơ chế xác minh danh tính qua Số điện thoại khôi phục:
- **Bước 1: Màn hình Selection:** Google liệt kê các phương thức, trong đó có: `Nhận mã xác minh tại ••••••••24 (Số điện thoại khôi phục)`.
- **Bước 2: Màn hình Xác nhận số điện thoại:** Google KHÔNG gửi mã ngay mà yêu cầu: *"Để có được mã xác minh, đầu tiên hãy xác nhận số điện thoại bạn đã thêm vào tài khoản của mình ••••••••24"*.
- **Bước 3: Màn hình Nhập mã 6 số:** Sau khi bấm nút "Gửi", Google mới thực sự phát SMS chứa mã 6 số về thiết bị.

## 2. Thông tin số điện thoại của User Tad
- **Số điện thoại chuẩn:** `0906746624` (SĐT đuôi 24 là số cá nhân của Tad).
- **Quy tắc điều phối:** Khi gặp màn hình xác minh này, điền đầy đủ số `0906746624`, click nút `Gửi`, sau đó DỪNG lại hỏi Tad để lấy mã OTP 6 số. TUYỆT ĐỐI CẤM tự mò mẫm hay retry bừa bãi.

## 3. Pitfall: Xung đột Selector giữa ô xác nhận SĐT và ô nhập OTP SMS
Đây là lỗi kỹ thuật nghiêm trọng trong Playwright DOM interaction:
- Cả hai ô nhập trên Google (`input#phoneNumberId` và ô nhập mã `input#idvPin`) đều có thể chia sẻ thuộc tính `input[type="tel"]`.
- **Hậu quả:** Nếu locator cho ô xác nhận SĐT dùng `input[type="tel"]`, sau khi bấm "Gửi" và chuyển sang màn hình nhập mã 6 số, locator SĐT vẫn tìm thấy `input[type="tel"]` (chính là ô nhập OTP!). Script sẽ tiếp tục điền lại 10 số `0906746624` vào ô OTP, gây lỗi *"Sai số lượng. Hãy thử lại"* và vòng lặp vô tận.

### Giải pháp selector triệt để:
- **Ô xác nhận SĐT (Bước 2):** CHỈ target bằng ID/name chuyên biệt:
  ```python
  phone_confirm_inp = page.locator('input#phoneNumberId, input[name="phoneNumber"]').first
  ```
  *(Tuyệt đối KHÔNG gộp `input[type="tel"]` vào selector này)*.
- **Ô nhập mã OTP 6 số (Bước 3):**
  ```python
  sms_code_inp = page.locator('input#idvPin, input[name="Pin"], input[name="idvPin"]').first
  ```
