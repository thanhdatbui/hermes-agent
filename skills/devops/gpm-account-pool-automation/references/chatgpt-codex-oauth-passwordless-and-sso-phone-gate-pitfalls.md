# Pitfalls: OpenAI Codex OAuth & ChatGPT Session Re-Authentication

## 1. CẤM TUYỆT ĐỐI Google SSO Khi Đăng Nhập / Re-auth OpenAI
- **Hiện tượng:** Khi session ChatGPT trên GPM profile bị hết hạn (`Phiên của bạn đã kết thúc` hoặc `Choose an account to continue`), nếu bấm nút **"Tiếp tục với Google" (Google SSO)** thì OpenAI lập tức chặn lại bằng màn hình `https://auth.openai.com/add-phone` (*Cần có số điện thoại*).
- **Nguyên nhân:** Các tài khoản ban đầu được đăng ký qua luồng Email + OTP riêng (hoặc Hotmail passwordless). Khi bấm Google SSO qua IP proxy, OpenAI coi đó là một luồng liên kết/tạo mới tài khoản qua identity provider mới và kích hoạt bot-check SMS.
- **Kỷ luật cứng:**
  - **CẤM bấm Google SSO** trong bất kỳ script tự động OAuth hay re-login OpenAI nào.
  - Luôn sử dụng đúng Email và mật khẩu đã lưu (`PASS CHATGPT`).

## 2. Passwordless vs Email Password Trong Đăng Ký ChatGPT
- Nhiều tài khoản khi đăng ký trước đây được OpenAI chuyển thẳng từ nhập Email sang bước nhập OTP (`Mã xác minh tạm thời của bạn cho ChatGPT`) mà không xuất hiện form nhập password.
- Những tài khoản này thuộc dạng **Passwordless**. Mật khẩu hòm thư Gmail/Hotmail KHÔNG PHẢI là mật khẩu của ChatGPT.
- Nếu gõ nhầm mật khẩu hòm thư vào form password của OpenAI, hệ thống sẽ báo `Incorrect email address or password`.
- **Giải pháp đúng chuẩn cho tài khoản mới (Hotmail):**
  - Đồng bộ `PASS CHATGPT` trong workbook `taikhoan_dat_v2_updated .xlsx`.
  - Nếu OpenAI hỏi password thì điền `PASS CHATGPT`, nếu passwordless thì chỉ cần giữ session sống trong profile GPM.

## 3. Quy Trình OAuth Codex Thành Công Không Tốn SMS (Zero SMS)
- Điều kiện tiên quyết: Profile GPM phải có session ChatGPT sống (vừa đăng ký hoặc ngâm xong mở lên còn đăng nhập).
- Khi mở URL Codex OAuth (`https://auth.openai.com/oauth/authorize?...`):
  1. Trình duyệt hiện màn hình: `Welcome back - Choose an account to continue to Codex`.
  2. Script chỉ cần click vào card tài khoản mục tiêu (`button:has-text('{email}')`).
  3. Màn hình Consent hiện ra (`Continue` / `Authorize`), click nút `Continue`.
  4. OpenAI chuyển hướng về callback port `1455` của OmniRoute với mã Authorization Code.
  5. Profile GPM được đóng sạch sẽ trong `finally`.
  - **Hoàn toàn KHÔNG xuất hiện màn hình hỏi số điện thoại, KHÔNG tốn 1 xu chi phí sim.**
