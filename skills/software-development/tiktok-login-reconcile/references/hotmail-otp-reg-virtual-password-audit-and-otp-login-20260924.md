# Hotmail OTP Reg "Pass Ảo" Audit & Luồng Phục Hồi Auto-Login OTP (2026-09-24)

## 1. Bối cảnh & Hiện tượng (Incident Máy 40 & Batch Feed Ca 3)
- Ca nuôi feed trên Máy 40 phát hiện thiếu nick `gabruync3o9` (Tik 6, Folder 318, Excel row 318).
- Cơ chế auto-login tự động kích hoạt:
  `python D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py 40 --email gabruync3o9 --ss --allow-parent-lock`
- Script đọc Excel thấy có ID `gabruync3o9` và PASS `jWGliO5H%1ih77` nên nhập cặp ID + Pass này.
- TikTok từ chối mật khẩu, hiển thị:
  > *"Sai tài khoản hoặc mật khẩu. Còn 1 lần nhập. Hãy thử lại."*
- Script timeout (388s) và fallback reconcile cũng timeout 600s -> Báo `manual-needed:account-switcher-missing-expected`.

## 2. Root Cause Kỹ Thuật: Cơ Chế "Pass Ảo" Trong Code Cũ Trước Ngày 17/09/2026
1. **Bản chất luồng đăng ký Hotmail OTP / Magic Link**:
   - Khi `social_reg_v1.py` đăng ký bằng Hotmail, TikTok xác thực qua Magic Link hoặc mã OTP 6 số từ hộp thư rồi vào thẳng màn tạo biệt danh/Hồ sơ mà **không mở màn hình "Tạo mật khẩu"**.
   - Do đó, tài khoản hoàn toàn chưa từng được tạo mật khẩu tĩnh trên máy chủ TikTok (tài khoản thuần Passwordless).
2. **Lỗ hổng sinh pass tự chế trước commit `61181f42`**:
   - Trước ngày 17/09/2026, hàm `ensure_profile_completed_and_track` chứa dòng mã:
     `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`
   - Khi `tiktok_pw` rỗng, script tự động sinh ngẫu nhiên một chuỗi mật khẩu (`make_tiktok_password`) và ghi thẳng vào Cột D (PASS) của file Excel `taikhoan_dat_v2_updated .xlsx`.
   - Kết quả: Excel có pass, nhưng máy chủ TikTok **chưa từng lưu pass này**.
   - Commit `61181f4265e3370aa14ec1efb92fd1175e5b615d` ngày 17/09/2026 đã vá triệt để: ép để trống `tiktok_pw` nếu flow không qua màn tạo pass. Tuy nhiên, các tài khoản đăng ký trước đó vẫn còn lưu pass ảo trên Excel.

## 3. Quy Mô Toàn Farm (Audit Excel `taikhoan_dat_v2_updated .xlsx`)
- Tổng số tài khoản TikTok trong workbook: 634 accounts.
- Số tài khoản đã có 2FA TOTP (Cột E): 453 accounts (an toàn, đã hoàn thành Phase B đổi pass thật).
- Số tài khoản chưa có 2FA (Cột E rỗng): 181 accounts. Trong đó:
  - 20 accounts: Cột D rỗng (đúng chuẩn passwordless mới sau 17/09).
  - 161 accounts: Cột D có pass. Trong đó có tới **143 accounts là Hotmail/Outlook** (88.8%).
- Phân bố 143 nick Hotmail dính pass ảo theo ngày reg:
  - 25/08/2026: **86 accounts** (cùng đợt với Máy 40).
  - 16/09/2026: 18 accounts.
  - 17/09/2026: 14 accounts.
  - 13/09/2026: 7 accounts.
  - 14/09/2026: 4 accounts.
  - Các ngày khác: 14 accounts.
- **Hệ quả**: Tất cả 143 accounts này nếu dùng `TikTok ID + Pass cột D` đăng nhập sẽ 100% bị TikTok báo *"Sai tài khoản hoặc mật khẩu"*.

## 4. Giải Pháp Phục Hồi Chuẩn (Recovery Contract)
1. **Đăng nhập bằng Email OTP (`--otp-only`)**:
   - Khi login các tài khoản này (hoặc khi chỉ định `--otp-only`), script login bắt buộc:
     - Chọn `login_target = account["login_email"]` (thay vì ID).
     - Khi vào màn OTP, CẤM tap link *"Đăng nhập bằng mật khẩu"*.
     - Khi vào màn Password, tap link *"Đăng nhập bằng mã"* (hoặc quay lại màn OTP).
   - Đọc OTP siêu tốc (<1s) qua Microsoft Graph API bằng `refresh_token` và `client_id` từ `D:\Taadaa\Hotmail\hotmail_all_60_bought.txt`.
2. **Khởi tạo Pass Thật & Kích Hoạt 2FA (Phase B)**:
   - Ngay sau khi nick đã vào Switcher máy, kích hoạt ngay `tiktok-add-bao-mat-f2a`:
     ```bash
     python python_runner/run_capture_phase_b.py \
       --machine <M> --serial <SERIAL> --expected-username <ID> --source-row <EXCEL_ROW> \
       --workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
       --workbook-sheet "Tài Khoản" --live
     ```
   - Quá trình này sẽ:
     1. Bật 2FA Authenticator TOTP -> ghi Secret 32 ký tự vào Cột E.
     2. Vào màn đổi/tạo mật khẩu, dùng OTP mail vượt xác minh danh tính, đặt mật khẩu mạnh ngẫu nhiên thật trên TikTok -> ghi đè mật khẩu thật vào Cột D.
     3. Khép kín vòng đời: tài khoản từ "pass ảo" trở thành tài khoản có đầy đủ ID + Pass thật + 2FA TOTP.
