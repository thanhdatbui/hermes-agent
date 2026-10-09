# Codex OAuth Verification & Hotmail-to-ChatGPT Combo Architecture

## 1. Nguyên Tắc Combo 1 Lượt: [Hotmail Login ➔ ChatGPT Reg Ngay]
- **Yêu cầu sống còn của User:** TUYỆT ĐỐI KHÔNG login Hotmail hàng loạt rồi để đó mới đi reg ChatGPT.
- **Quy trình 1 lượt (Single-pass combo):**
  1. Worker mở profile GPM (trên proxy riêng biệt, max 5 workers song song).
  2. Đăng nhập Hotmail thành công (vượt qua màn hình Điều khoản & Cookie).
  3. **Ngay lập tức điều hướng sang `chatgpt.com` để đăng ký tài khoản ChatGPT luôn trong cùng session**.
  4. Hoàn tất ChatGPT bằng OTP Graph API -> Chụp ảnh bằng chứng (`*_chatgpt_reg_success.png`).
  5. Đóng sạch profile và đưa tài khoản vào trạng thái `WAIT_24_48H` (ngâm chờ Codex).

## 2. Codex OAuth Verification: Session-Based vs Google SSO Phone Gate
Khi đưa tài khoản ChatGPT đã ngâm đủ 24-48h đi xác thực Codex OAuth (`auth.openai.com/oauth/authorize`):

### A. Tài khoản có sẵn Cookie / Active Session (Pass 100% không tốn SMS):
- Khi profile GPM mở lên, OpenAI nhận diện được session ChatGPT đang sống.
- Giao diện xuất hiện màn hình:
  `Welcome back - Choose an account to continue to Codex`
- **Cách xử lý:** 
  - Locator: `button:has-text('<email>'), [role='button']:has-text('<email>'), a:has-text('<email>')`
  - Bấm chọn tài khoản -> Bấm `Continue / Authorize`.
  - Callback port 1455 nhận mã Authorization Code ngay lập tức.
  - **HOÀN TOÀN KHÔNG BẮT XÁC MINH SỐ ĐIỆN THOẠI HAY TỐN PHÍ SIM.**

### B. Tài khoản mất Session / Bấm qua "Continue with Google" (Phone Wall):
- Nếu session cũ bị văng hoặc đăng xuất (`Phiên của bạn đã kết thúc`).
- **CẤM TUYỆT ĐỐI:** Bấm nút `Continue with Google` (Google SSO).
- **Hiện tượng thực tế:** Ngay khi bấm Google SSO, cơ chế bảo vệ của OpenAI sẽ lập tức redirect sang `https://auth.openai.com/add-phone` (*Cần có số điện thoại - OpenAI*), đòi nhập số điện thoại để nhận SMS (+1 hoặc SIM thật).
- **Quy tắc:** Chỉ được ủy quyền OAuth khi profile còn session sống hoặc đăng nhập bằng Email/Password/OTP trực tiếp. Nếu vướng Phone Gate, đánh dấu tài khoản cần khôi phục session, không cố tình click Google SSO gây kẹt.

## 3. Post-Login Interstitials Trên Hotmail
- **Nút "Tiếp" trên Điều khoản (`account.live.com/tou/accrue`):**
  - Microsoft đổi text nút thành `Tiếp` (thay vì `Tiếp tục` / `Next`).
  - Cần bộ selector: `input[value*='Tiếp'], input[value*='tiếp'], button:has-text('Tiếp'), .btn-primary, input[type='submit']`.
- **Cookie Consent Banner:**
  - Selector: `button:has-text('Accept'), button:has-text('Chấp nhận'), #acceptButton, #onetrust-accept-btn-handler`.
  - Phải dùng `.first.click(force=True)` để không bị lỗi element handle khi trang có nhiều nút trùng tên hoặc nút nằm dưới overlay.
- **KMSI ("Duy trì đăng nhập?"):**
  - Selector `#idSIButton9`, nút `Có` / `Yes`.
