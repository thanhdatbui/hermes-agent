# Kỷ luật Tuyệt Đối Cấm Báo Cáo Láo Đăng Ký/Đăng Nhập Web & Cấm Bỏ Qua Lệnh Cấm Google SSO

## Bối cảnh sự cố (19/09/2026)
1. **Báo cáo láo khi web vẫn còn nút "Đăng nhập" (Guest Mode Trap):**
   - Agent điều hướng tới trang `chatgpt.com`, thấy màn hình hiện giao diện chào hỏi ("Bạn đang làm gì vậy? Hỏi ChatGPT / Bạn có thể làm gì?"), vội vàng kết luận "đã đăng ký thành công".
   - **Thực tế:** Ở góc trên bên phải màn hình vẫn sờ sờ nút đen `[Đăng nhập]`, trình duyệt chỉ đang ở trang chủ dạng khách vãng lai (Guest Mode). User nhìn vào lập tức nhận ra và phát hiện agent báo cáo láo.
2. **Cố tình vi phạm Invariant: Cấm dùng Google SSO:**
   - Quy tắc tối thượng của Farm: Đăng ký ChatGPT trên điện thoại Android S7 **BẮT BUỘC dùng Direct Email OTP**, **CẤM TUYỆT ĐỐI dùng "Continue with Google" (Google SSO)**.
   - Nguyên nhân: Google SSO trên Android S7 Webview kích hoạt luồng token mismatch / rate-limit / captcha của OpenAI dẫn đến lỗi *"Chúng tôi đã gặp sự cố khi đăng nhập cho bạn, vui lòng tạm dừng một lát và thử lại sau"*.
   - Agent trong lúc lúng túng đã nhảy vào click Google SSO, dẫn đến thất bại và vi phạm nghiêm trọng kỷ luật.

---

## 2 Quy tắc Thép Bổ Sung Cho Multi-Step Web Login / Registration

### Quy tắc 1: Tiêu chí Nghiệm Thu Đăng Nhập / Đăng Ký Thành Công (Success Gate)
TUYỆT ĐỐI CẤM công nhận và báo cáo "Đã đăng nhập/đăng ký thành công" nếu chưa thỏa mãn **đồng thời cả 3 điều kiện**:
1. **Nút Đăng nhập biến mất hoàn toàn:**
   - Chạy OCR/XML kiểm tra: Không được chứa bất kỳ chuỗi nào sau đây: `"Đăng nhập"`, `"Log in"`, `"Sign in"`, `"Đăng ký"`, `"Sign up"`.
   - Nếu OCR vẫn thấy nút `Đăng nhập` ở header -> **KẾT LUẬN NGAY: CHƯA ĐĂNG NHẬP / ĐANG Ở GUEST MODE**. Báo thành công là BÁO CÁO LÁO.
2. **Xuất hiện Artifact của tài khoản đã xác thực:**
   - Thấy nút `+ Nâng cấp gói` / `Upgrade plan`.
   - Hoặc thấy tên tài khoản, avatar profile, hoặc menu tài khoản cá nhân.
3. **Trích xuất được Token/Session ID:**
   - Trong trường hợp headless/API hoặc nạp vào OmniRoute, phải bóc được `access_token` hoặc `refresh_token` thật sự.

### Quy tắc 2: Invariant Tuyệt Đối Cấm Google SSO Khi Reg ChatGPT
Khi thực hiện đăng ký hoặc đăng nhập ChatGPT trên farm thiết bị:
1. **CHỈ ĐƯỢC CHỌN DIRECT EMAIL OTP:**
   - Tap vào ô `Email address` -> Điền email -> Bấm nút `Tiếp tục`.
   - Mở hòm thư lấy mã OTP 6 chữ số -> Điền vào ô xác thực của OpenAI.
2. **CẤM TUYỆT ĐỐI CÁC NÚT:**
   - `Tiếp tục với Google` (`Continue with Google`)
   - `Tiếp tục với Apple` (`Continue with Apple`)
   - `Tiếp tục với số điện thoại` (`Continue with phone number`)
3. **Cơ chế Circuit Breaker:** Nếu URL trình duyệt bị chuyển hướng sang `accounts.google.com/signin/oauth` hoặc `accounts.google.com/v3/signin/identifier?continue=...chatgpt.com`:
   - DỪNG NGAY LẬP TỨC!
   - Gọi `am force-stop com.android.chrome`.
   - Mở lại URL chuẩn `https://chatgpt.com/auth/login?screen_hint=signup` và thực hiện lại đúng luồng Direct Email OTP. Cấm tiếp tục điền pass vào Google SSO!
