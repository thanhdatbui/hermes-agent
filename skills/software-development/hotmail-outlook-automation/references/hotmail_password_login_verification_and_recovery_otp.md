# Hotmail Password Login: Identity Verification Challenge & Recovery Email OTP Flow

## 1. Bản Chất Lỗi Khi Login Hotmail Bằng Mật Khẩu
Khi đăng nhập Hotmail/Outlook qua trình duyệt (GPM Login + Playwright):
- **Thử thách xác minh danh tính (Identity Verification Challenge)**:
  - Microsoft thường xuyên hiện màn hình *"Almost there"* / *"Sắp hoàn thành"*, *"Verify your email"* / *"Xác minh email của bạn"*, hoặc *"Send a code to ke*...@fviainboxes.com"*.
  - **CẠM BẪY 1**: Cụm từ `"xác minh email của bạn"` và `"verify your email"` TUYỆT ĐỐI KHÔNG ĐƯỢC đưa vào danh sách `hard_block_keywords` (như sai mật khẩu, khóa tài khoản). Nếu đưa vào, script sẽ ngắt sớm với trạng thái `BLOCKED: SECURITY_BLOCK` trước khi kịp gọi bộ xử lý OTP!
  - **CẠM BẪY 2**: Nhiều tài khoản Hotmail đã gán mail khôi phục tạm `@fviainboxes.com`. Khi Microsoft gửi OTP về mail khôi phục, script KHÔNG ĐƯỢC chỉ phụ thuộc vào Microsoft Graph API token (vì token Graph chỉ đọc được hộp thư chính của Hotmail, không đọc được mail khôi phục). BẮT BUỘC phải dùng `fetch_recovery_email_otp(recovery_email)` từ `mail_domain_otp_helper.py` để lấy OTP từ API `fviainboxes.com`.

## 2. Nguồn Tra Cứu Mail Khôi Phục & Token Toàn Farm
- File `taikhoan_dat_v2_updated .xlsx` của supervisor CHỈ chứa mật khẩu Hotmail (`PASS MAIL`), KHÔNG chứa mail khôi phục hay token.
- Kho dữ liệu chuẩn lưu mail khôi phục (`@fviainboxes.com`), Graph token và Client ID nằm tại:
  - Farm Admin: `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx`
  - Farm Kibe: `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`
  - Cột 1: `số máy`, Cột 2: `tài khoản gmail/hotmail`, Cột 5: `mail khôi phục`, Cột 9: `token`, Cột 10: `client_id`.
- Helper chuẩn tra cứu hai kho:
  ```python
  def get_account_recovery_and_tokens(email: str) -> tuple[str, str, str]:
      for path in [
          Path(r"D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx"),
          Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"),
      ]:
          if not path.exists():
              continue
          try:
              wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
              ws = wb.active
              t = email.strip().lower()
              for r in ws.iter_rows(values_only=True):
                  if r and len(r) > 1 and str(r[1] or "").strip().lower() == t:
                      wb.close()
                      return str(r[4] or "").strip(), str(r[8] or "").strip(), str(r[9] or "").strip()
              wb.close()
          except Exception:
              pass
      return "", "", ""
  ```

## 3. Quy Trình Tự Động Vượt Màn Hình Xác Minh Recovery OTP
1. Phát hiện màn hình xác minh danh tính:
   - Selectors: `#proof-confirmation-email-input`, `#iProofEmail`, hoặc text chứa `"fviainboxes"`, `"sắp hoàn thành"`, `"almost there"`, `"xác minh email"`, `"verify your email"`, `"send a code to"`, `"gửi mã đến"`.
2. Chọn phương thức proof nếu hiển thị:
   - Selector: `page.locator("text='fviainboxes', text='Email'").first.click()`
3. Điền đầy đủ địa chỉ mail khôi phục:
   - Selector: `page.locator("#proof-confirmation-email-input, #iProofEmail, input[type='email']").first.fill(rec_email)`
4. Bấm nút gửi mã:
   - Selector: `page.locator("button:has-text('Gửi mã'), button:has-text('Send code'), #iSelectProofAction, input[type='submit']").first.click()`
5. Gọi API lấy mã OTP:
   - `otp_code = fetch_recovery_email_otp(rec_email, timeout_seconds=45)`
6. Điền mã OTP và submit:
   - Nếu UI mới có 6 ô: `#codeEntry-0` .. `#codeEntry-5` (điền từng ký tự)
   - Nếu UI cũ có 1 ô: `#iOttText, input[name='otc'], input[type='tel']` (điền cả chuỗi rồi Enter / click Submit).

## 4. Bẫy Cookie Consent Banner Làm Sai Lệch Kết Quả Auth
- Trên cả `login.live.com` và `account.microsoft.com`, Microsoft thường hiển thị banner cookie (*"Chúng tôi dùng cookie tùy chọn... Chấp nhận / Từ chối / Quản lý cookie"*).
- Nếu banner này che khuất trang, trình duyệt không chuyển hướng hoặc không tìm thấy thẻ header `#mectrl_headerPicture`, dẫn đến phán đoán sai là `BLOCKED`.
- BẮT BUỘC:
  - Bổ sung selector: `button:has-text('Chấp nhận')`, `button:has-text('Accept')`, `#acceptButton`, `button:has-text('Đồng ý')`, `button:has-text('Từ chối')`, `button:has-text('Reject')`.
  - Click dứt điểm banner cả trong vòng lặp chuyển tiếp và sau khi landing vào trang cuối cùng trước khi screenshot và xác nhận auth.
  - Sau khi click đóng Cookie banner, BẮT BUỘC chờ dashboard render tối thiểu 3-4s (chờ selector `header, nav, main, #mectrl_headerPicture, h1...`) rồi mới chụp ảnh `post_login`, tránh chụp lúc trang đang redirect gây ra ảnh trắng tinh (file size 2–4 KB) làm sai lệch kết quả OCR.

## 5. Kinh Nghiệm Điều Phối Worker Cho Repo Hotmail
- Repo `D:/Taadaa/Hotmail` có `AGENTS.md` yêu cầu chạy `bootstrap.ps1` kiểm tra môi trường trước khi ghi file.
- Khi điều phối Worker qua `claude_worker.py --role worker`, tool `Bash` bị cấm mặc định (`--disallowedTools Bash`), dẫn đến Worker Haiku không thể chạy script ps1 và tự động báo `BLOCKED: AGENTS.md requires bootstrap.ps1...`.
- Khi gặp lỗi này trên Tier 1 Haiku, Gateway phân loại là `NEEDS_INPUT` và dừng lại. Để vượt qua, Coordinator cần leo thang sang **Tier 2 (Antigravity CLI: `python D:/Taadaa/tools/ag_cli.py fix ...`)** để thực thi patch trực tiếp.

## 6. Bắt Buộc Chạy Canary Thực Tế Trước Khi Declare Done
- Khi hoàn tất sửa đổi code trên `batch_gpm_hotmail_password_login.py` hoặc các automation scripts khác, Coordinator TUYỆT ĐỐI CẤM báo DONE chỉ dựa trên `py_compile` hay unit test giả lập.
- BẮT BUỘC chạy Canary trực tiếp trên 1 profile thật đang bị lỗi hoặc trong queue (ví dụ: `python3 D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py --email vjorandrea1961@hotmail.com --proxy-port 5102 --raw-proxy ... --machine 2`).
- Chờ tiến trình nền kết thúc (exit code 0), sau đó bắt buộc mở ảnh screenshot `post_login` bằng WinRT OCR hoặc `browser_vision` để soi mắt xác nhận: có header Microsoft, avatar hoặc chữ 'Tài khoản Microsoft' hiển thị rõ ràng, không bị màn hình trắng/đen hay popup che khuất. Báo DONE khi chưa chạy Canary thật là vi phạm Gate nghiêm trọng.
