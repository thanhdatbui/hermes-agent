# Codex OAuth & ChatGPT Session Security Rules

## 1. TUYỆT ĐỐI CẤM GOOGLE SSO
- **Quy tắc cứng:** CẤM TUYỆT ĐỐI bấm nút "Tiếp tục với Google" / "Continue with Google" trong mọi luồng đăng nhập OpenAI, ChatGPT hoặc ủy quyền Codex OAuth.
- **Lý do kỹ thuật:** Khi đăng nhập lại bằng Google SSO trên IP proxy, OpenAI coi đó là liên kết tài khoản mới từ môi trường lạ và **LẬP TỨC KÍCH HOẠT MÀN HÌNH BẮT VER SỐ ĐIỆN THOẠI SMS (`add-phone`)**.
- **Giải pháp:** 100% tài khoản phải đăng nhập bằng Email + Mật khẩu (`PASS CHATGPT`), hoặc dùng session cookie có sẵn trong GPM profile.

## 2. CƠ CHẾ BẢO VỆ CHỐNG VER SỐ (PHONE CHECKPOINT) KHI OAUTH CODEX
- **Hiện tượng:** Cùng một tài khoản ChatGPT, nếu vừa mới tạo lại session (fresh login/signup) mà đem đi gọi link OAuth Codex (`auth.openai.com/oauth/authorize`) ngay lập tức, OpenAI sẽ đánh giá rủi ro bảo mật client cao và chuyển hướng sang `auth.openai.com/add-phone` đòi số điện thoại.
- **Nguyên nhân:** OAuth Codex yêu cầu trust score cao hơn so với lướt web ChatGPT thông thường.
- **Giải pháp bắt buộc (Ngâm Session >= 24h - 48h):**
  - Tài khoản sau khi đăng ký ChatGPT bằng Email + OTP thành công, session ChatGPT phải được **LƯU NGUYÊN VẸN TRÊN GPM PROFILE**.
  - **BẮT BUỘC NGÂM PROFILE TỐI THIỂU 24h - 48h** ở trạng thái tĩnh.
  - Khi session đã có độ tuổi (trust score cao), mở link OAuth Codex lên sẽ hiện thẻ chọn tài khoản (`Welcome back - Choose an account`) -> Click thẻ -> Bấm `Continue/Authorize` -> Cấp token thành công **100% KHÔNG BỊ HỎI SỐ ĐIỆN THOẠI**.

## 3. CHECKLIST XỬ LÝ NICK BỊ VĂNG SESSION
- Nếu một nick bị văng session (hết hạn cookie):
  1. Tuyệt đối không bấm Google SSO.
  2. Phải đăng nhập lại bằng Email + Mật khẩu đã tạo lúc reg (hoặc Reset Password qua Email OTP).
  3. Sau khi khôi phục session, **KHÔNG ĐEM ĐI OAUTH CODEX NGAY** mà phải đưa lại vào trạng thái `WAIT_24_48H` ngâm tiếp trước khi đem đi ver Codex.
