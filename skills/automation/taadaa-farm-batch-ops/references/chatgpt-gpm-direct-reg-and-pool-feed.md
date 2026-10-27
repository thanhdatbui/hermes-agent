# ChatGPT Web GPM Direct Registration & Pool Feeding Playbook

## 1. Bản Chất Tài Khoản Hotmail & Quy Trình Nạp ChatGPT
- **Không có "reg Hotmail":** Toàn bộ Hotmail trên farm là tài khoản mua sẵn (từ các đợt mua `latest_bought_*.txt`, `hotmail_all_60_bought.txt`).
- **Pipeline chuẩn 2 bước:**
  1. `HOTMAIL_LOGIN`: Đăng nhập hòm thư Hotmail đã mua vào GPM profile bằng `mail_password`.
  2. `CHATGPT_REG`: Dùng hòm thư Hotmail đó để đăng ký tài khoản ChatGPT mới trên web.
- **Dấu hiệu nhận biết tài khoản chưa từng reg ChatGPT:** Khi submit email, OpenAI chuyển hướng sang màn hình **"Bạn bao nhiêu tuổi?" (`/about-you`)**. Đây là Onboarding của luồng tạo tài khoản mới lần đầu. Nếu thấy màn này, profile **CHƯA HỀ có tài khoản ChatGPT trước đó** (không được coi là tài khoản đã reg).

## 2. Kỷ Luật Mật Khẩu Chống Pattern Detection (Anti-Bot Footprint)
- **CẤM NỐI CHUỖI TĨNH CỐ ĐỊNH:** Tuyệt đối không dùng chuỗi cố định (như `@Taadaa2026`) để bù độ dài >= 12 ký tự cho các mật khẩu mail ngắn. OpenAI quét pattern đuôi cố định sẽ truy vết và trảm hàng loạt cả cụm.
- **CSPRNG Salt ngẫu nhiên per-account:** Bắt buộc dùng module `secrets` sinh salt ngẫu nhiên đa dạng (chữ hoa, chữ thường, số, ký tự đặc biệt `@#$%!&*`) để mọi tài khoản có mật khẩu độc nhất.
- **Persistence bắt buộc:** Mật khẩu sau khi tạo phải được ghi đè lưu trữ ngay vào cột `PASS CHATGPT` (cột L) của file Excel tương ứng (`kibe` và `admin`).

## 3. Quản Trị Dữ Liệu Excel & Bẫy Lệch Schema Kibe vs Admin
- **File `gmail_clean_v2.xlsx`:** Tên file giữ theo legacy, nhưng chứa 100% tài khoản Hotmail kèm Microsoft Graph refresh token (cột 9) và client ID (cột 10) để bóc tách OTP.
- **Đối chiếu 1:1 theo Email:** Luôn map trực tiếp theo email Hotmail của profile, không map chéo sang Gmail.
- **Lệch Schema:** File Kibe có 12 cột (cột 11 là `PASS CHATGPT`), file Admin ban đầu chỉ có 10 cột. Code đọc Excel phải tự tạo header nếu thiếu cột, không được `continue` bỏ qua ứng viên rồi `return 0` làm supervisor tưởng nhầm đã reg xong.
- **Exit Code nghiêm ngặt:** Nếu không tìm thấy ứng viên hợp lệ hoặc đăng ký thất bại, bắt buộc trả về `exit code 1`. Chỉ `return 0` khi kết quả thực tế là `SUCCESS`, `ALREADY_LOGGED_IN` hoặc `DRY_RUN_OK`.

## 4. Playwright & Microsoft Graph OTP Verification
- **Pre-validate Graph Token:** Ping endpoint token của Microsoft (`login.microsoftonline.com`) để xác thực refresh token trước khi mở GPM browser. Nếu token chết (AADSTS70000), skip ngay để tránh mở browser treo 60s chờ OTP vô ích.
- **Tránh gõ nhầm OTP vào ô Email Readonly:** Tại trang nhập mã OTP của OpenAI, ô email cũ hiển thị dưới dạng `<input readonly value="...">`. Selector nhập mã OTP bắt buộc phải loại trừ `[readonly]` hoặc dùng chính xác `input[name="code"]`.
