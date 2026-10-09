# ChatGPT Canary SSO Bypass & Email Submit Tuning trên S7

## 1. Google SSO Bottom-sheet Handling
Khi Chrome mở trang auth của OpenAI (`auth.openai.com`), trình duyệt thường bật popup Google SSO hoặc gợi ý tài khoản đã đăng nhập trong máy.
- **Dấu hiệu nhận diện trong UI XML:**
  - `Đăng nhập bằng Google`, `Sign in with Google`
  - `Tiếp tục bằng tài khoản của`, `Continue as`
  - `Chọn tài khoản`, `Choose an account`
  - `Lưu mật khẩu`, `Save password`
  - `Đã đăng nhập vào Google bằng`, `Signed in to Google as`
- **Xử lý an toàn:**
  - BẮT BUỘC bấm `Bỏ qua` / `Hủy` / `Cancel` / `Dismiss` / `Không phải bây giờ`.
  - Fallback tap vào vùng mép dưới (ví dụ `(540, 1780)` trên S7 1080x1920) hoặc tap vùng trống phía trên (`(540, 300)`) để đóng bottom-sheet mà không chọn tài khoản Google.
  - CẤM tap chọn tài khoản liên kết Google vì sẽ gây sai lệch luồng email/pass độc lập.

## 2. EMAIL_SUBMIT_TIMEOUT Pitfall
- **Triệu chứng:** Sau khi gõ email và bấm "Tiếp tục" (Continue), flow bị treo ở bước submit email quá 80s-120s mà không chuyển sang màn hình OTP (`FAILED_AT_EMAIL_SUBMIT`, `reason_code: EMAIL_SUBMIT_TIMEOUT`).
- **Nguyên nhân tiềm ẩn:**
  - Cloudflare Turnstile / Bot challenge chạy ngầm không tự vượt qua được trên WebView/Chrome cũ của S7.
  - Network stall hoặc trang bị kẹt ở popup cookie / consent đè lên nút submit.
  - Ô input email bị mất focus hoặc ký tự email gõ qua `input text` bị thiếu ký tự đặc biệt khiến form không submit.
- **Biện pháp xử lý & debug:**
  - Luôn chụp screencap hiện trường khi timeout (`chatgpt_err_email_submit_*.png`) và kéo về máy host.
  - Kiểm tra xem có xuất hiện captcha, thông báo lỗi màu đỏ ("Email không hợp lệ", "Cần nhập email") hay spinner tải vô hạn.
  - Nếu xuất hiện dialog cookie/consent, bấm giải phóng trước khi tap nút "Tiếp tục".
