# ChatGPT Direct Registration on GPM (Email + Password + OTP Flow)

## 1. Bối cảnh & Khi nào dùng Direct Registration
Khi Gmail cũ đã đăng nhập trên profile GPM (đã có cookie Google / Gmail live trong profile), nếu sử dụng nút "Continue with Google" (OAuth), một số tài khoản có thể gặp checkpoint bảo mật hoặc lỗi liên kết OAuth.
Quy trình **Direct Registration** đăng ký tài khoản ChatGPT trực tiếp bằng Email + Password trên `https://chatgpt.com/auth/signup`:
- Không nhấn "Continue with Google".
- Sử dụng Password của Gmail (hoặc chuẩn hoá tối thiểu 12 ký tự với hậu tố nếu quá ngắn).
- Mở tab Gmail song song trên cùng profile để lấy mã OTP xác minh email từ OpenAI.
- Hoàn tất onboarding thông tin cá nhân (tên, ngày sinh / tuổi).

---

## 2. Chi tiết các bước kỹ thuật (Playwright CDP)

### Bước 0: Nhận diện dương tính Session đã đăng nhập sẵn (Positive Session Detection) & Xử lý Account Picker
Trước khi tiến hành đăng ký, luôn kiểm tra xem profile đã có session ChatGPT đang hoạt động hay không để tránh thao tác thừa:
1. **Xử lý Account Picker (Chào mừng trở lại / Welcome back)**:
   - OpenAI thường hiển thị màn hình chọn tài khoản nếu profile từng có phiên làm việc trước đó: `div:has-text("Chào mừng trở lại")`, `div:has-text("Welcome back")`, hoặc `div:has-text("Chọn một tài khoản")`.
   - Nếu phát hiện picker: tự động click vào nút/thẻ chứa `email` (`button:has-text("{email}")`, `div:has-text("{email}")`), hoặc click card đầu tiên (`div.account-item`, `button[data-testid*="account"]`) và chờ 3s để vào phiên làm việc.
2. **Tiêu chí nhận diện dương tính (`is_chatgpt_logged_in(page, email: str = "") -> bool`)**:
   - Xuất hiện các selector của ô chat chính: `#prompt-textarea`, `textarea[data-id="root"]`.
   - Hoặc URL thuộc `chatgpt.com` không chứa `/auth/` và body không còn text của màn hình Account Picker, đồng thời chứa các cụm chào mừng: `"chúng ta nên bắt đầu"`, `"what can i help with"`, `"đoạn chat mới"`, `"new chat"`.
3. **3 Checkpoint kiểm tra**:
   - Checkpoint A: Ngay sau khi mở `https://chatgpt.com/`.
   - Checkpoint B: Sau khi điều hướng tới URL đăng ký `https://chatgpt.com/auth/login?screen_hint=signup` (OpenAI sẽ tự động redirect về giao diện chat nếu session còn sống).
   - Checkpoint C: Ngay sau khi nhập email và click Continue (trước khi vào bước Password/OTP).
4. **Xử lý khi phát hiện đã đăng nhập**:
   - Chụp ảnh bằng chứng nghiệm thu `{email}_chatgpt_reg_success.png`.
   - Gọi ngay `mark_chatgpt_ready_excel(email)` để cập nhật cờ `CHATGPT_READY` vào Cột 14 của Master Excel.
   - Trả về status `ALREADY_LOGGED_IN` và kết thúc sớm an toàn, không gọi OTP hay gửi request dư thừa.

### Bước 1: Điều hướng & Nhập form đăng ký
1. Điều hướng page tới `https://chatgpt.com/auth/signup`.
2. Chờ input email (`input[name="email"]`, `#email-input`, hoặc selector tương đương).
3. Nhập email của profile. Bấm nút Continue.
4. Chờ input password (`input[name="password"]`).
5. **Chuẩn hoá Password**:
   - OpenAI yêu cầu mật khẩu tối thiểu 12 ký tự (hoặc chính sách mật khẩu mạnh).
   - Nếu mật khẩu trong sheet/DB ngắn hơn 12 ký tự: tự động thêm hậu tố chuẩn (ví dụ `@Taadaa2026`) để đạt độ dài an toàn.
   - Nhập mật khẩu và nhấn Continue.

### Bước 2: Lấy mã xác thực OTP qua tab Gmail song song & Xử lý Email Threading
1. Khi màn hình ChatGPT chuyển sang trạng thái chờ nhập mã 6 số (Verify your email).
2. Tạo/Mở một tab mới trên cùng context CDP: `context.new_page()`.
3. Điều hướng tới `https://mail.google.com/mail/u/0/#inbox`.
4. Tìm kiếm email gửi từ OpenAI (`OpenAI` hoặc `verification code` / `Verify your email`):
   - **Xử lý Threading trong Gmail (CỰC KỲ QUAN TRỌNG)**: Gmail gộp các email xác minh liên tiếp vào chung 1 hội thoại (thread). Tin nhắn mới nhất nằm ở **DƯỚI CÙNG** của thread.
   - Khi click vào thư, phải cuộn xuống đáy: `mail_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`.
   - Tìm và mở rộng các container tin nhắn bị thu gọn (collapsed): `locator('div[role="listitem"], div.kv, div.adn')` -> click vào tin nhắn cuối cùng để expand.
   - **Bốc mã OTP**: Dùng `re.findall(r"\b(\d{6})\b", text)` và LUÔN LẤY MÃ CUỐI CÙNG `nums[-1]`! Tuyệt đối không lấy `nums[0]` vì sẽ bị nuốt mã OTP cũ từ các lần thử trước.
5. Đóng tab Gmail (`mail_page.close()`).
6. Quay lại tab ChatGPT, nhập 6 số OTP vào form xác nhận (hoặc từng ô input số) và bấm Tiếp tục / Continue.

### Bước 3: Xử lý Onboarding "About you" (Bilingual Form)
ChatGPT có 2 biến thể giao diện Onboarding tùy theo locale / ngôn ngữ trình duyệt:
1. **Dạng 1: Ô Age (Tiếng Anh)**:
   - Input họ tên: `input[name="name"]` -> điền tên hợp lệ.
   - Input tuổi: `input[name="age"]` -> nhập tuổi (ví dụ ngẫu nhiên 22-28).
2. **Dạng 2: Ngày sinh (Tiếng Việt / Localization)**:
   - Các phần tử `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`.
   - Click và gõ số ngày (`10-28`), tháng (`01-12`), năm sinh (`1996-2002`).
3. Nhấn nút submit: `button[type="submit"]` hoặc text `Continue` / `Tiếp tục`.

---

## 3. Van an toàn & Hard Gate Nghiệm Thu (Anti-False-Positive)
1. **Hard Gate 1 — Hậu kiểm OTP**:
   - Ngay sau khi nhập OTP và submit, kiểm tra body text xem có xuất hiện thông báo lỗi:
     `mã không chính xác`, `incorrect code`, `invalid code`, `too many attempts`, `that code didn't work`.
   - Nếu phát hiện lỗi: Chụp ảnh bằng chứng (`_step6_otp_error.png`), lập tức gọi `unmark_chatgpt_ready_excel(email)` để dọn tag lỗi, trả về `FAIL_WRONG_OTP`. TUYỆT ĐỐI KHÔNG tiếp tục hay ghi nhận thành công.
2. **Hard Gate 2 — Điều kiện tiên quyết để ghi nhận SUCCESS**:
   - URL đích phải rời khỏi flow xác thực: không còn chứa `/auth/` và thuộc domain `chatgpt.com`.
   - Giao diện chat chính phải hiển thị thực sự: phát hiện phần tử chat (`textarea`, `#prompt-textarea`, hoặc nút `New chat` / `Đoạn chat mới`).
   - Xử lý kịp thời các modal onboarding / dismiss ("Okay, let's go", "Done").
   - Chỉ khi thoả mãn đồng thời cả 2 điều kiện trên mới được chụp ảnh `chatgpt_reg_success.png` và gọi `mark_chatgpt_ready_excel(email)`.
3. **Circuit Breaker**:
   - Nếu gặp 2 lỗi liên tiếp (ví dụ IP bị rate-limit, captcha chặn cứng, hoặc không đọc được OTP), dừng batch để bảo vệ proxy và profile.
4. **Cập nhật Master Excel & State**:
   - Ghi chú tag `CHATGPT_READY` vào cột `Ghi Chú` trong `master_gmail_manager.xlsx` (bảo tồn các ghi chú cũ).
   - Nếu thất bại, phải xóa sạch tag `CHATGPT_READY` nếu trước đó bị ghi nhầm.
   - Lưu trạng thái vào state file `D:\Taadaa\runtime\kibe\cron-state\gpm_chatgpt_direct_reg_state.json`.
