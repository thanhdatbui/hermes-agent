# Bẫy Mật Khẩu Backfilled Ảo Gây Sai Pass "Còn 1 Lần Nhập" & Timeout 1000s Trong Fast Auto-Login Ca Nuôi (2026-09-24)

## 1. Bối cảnh sự cố (Incident M40 - Ca 3 Tối 2026-09-24)
- **Hiện tượng**: Ca nuôi feed phát hiện thiếu nick `gabruync3o9` (Row 6) trong Switcher (app có 7/8 nick, nút "Thêm tài khoản" còn trống).
- **Hệ thống tự động kích hoạt**: Hook `_maybe_recover_missing_account_via_login` gọi:
  `python D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py 40 --email gabruync3o9 --ss --allow-parent-lock`
- **Kết quả thất bại**:
  - `tiktok_login_v1.py` đọc Excel thấy cột C (ID = `gabruync3o9`) và cột D (PASS = `jWGliO5H%1ih77`) đều có giá trị -> ưu tiên login bằng `ID` + `PASS`.
  - TikTok app trả về lỗi ngay tại màn hình mật khẩu:
    `"Sai tài khoản hoặc mật khẩu. Còn 1 lần nhập. Hãy thử lại."`
  - Script không có cơ chế fail-fast khi gặp text báo sai mật khẩu / cảnh báo số lần nhập còn lại -> treo chờ `wait_login_success` đến hết timeout 388s (`returncode=2`).
  - Runner tiếp tục fallback sang `reconcile_tiktok_accounts.py` (chạy thêm 600s cũng với dữ liệu cũ) -> tổng cộng máy kẹt ~1000s trước khi văng `manual-needed`.

## 2. Root Cause
- Tài khoản `gabruync3o9` đăng ký ngày 25/08/2026 qua luồng Hotmail OTP/Magic Link (passwordless). Lúc reg không qua màn hình đặt mật khẩu tĩnh (`fill_password_and_login` không thấy màn pass nên gán `tiktok_pw = ""`).
- **Nguồn gốc mật khẩu sai trên Excel**: Trước commit `61181f42` (17/09/2026), hàm `ensure_profile_completed_and_track` trong `social_reg_v1.py` có logic fallback tự chế pass:
  `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`
  Khi flow không có màn tạo pass (`tiktok_pw = ""`), toán tử `or` tự động gọi `make_tiktok_password()` sinh random chuỗi `jWGliO5H%1ih77` rồi ghi vào cột D (PASS) của Excel `taikhoan_dat_v2_updated .xlsx`. Nghịch lý: Excel có pass nhưng server TikTok CHƯA TỪNG được set pass này!
- Đến ngày 17/09/2026 (commit `61181f42`), rule `User rule 2026-08-16` mới được vá triệt để: cấm make_tiktok_password tự chế, flow không pass thì để trống `None` (như Tik 8 `kanyeujfauq` reg ngày 22/09 cột pass để trống chuẩn). Các nick reg trước ngày 17/09 (như Tik 6 & 7 của M40) bị tồn đọng pass rác tự chế trên Excel.
- Điều kiện chọn target login trong `tiktok_login_v1.py`:
  `login_target = (account.get("id") or "").strip() if (account.get("id") and account.get("tiktok_pass")) else account["login_email"]`
  ngộ nhận rằng có `tiktok_pass` là có thể đăng nhập bằng ID+Pass, trong khi với các nick reg OTP chưa reset pass thì mật khẩu cột D hoàn toàn vô hiệu.
- Nguy cơ P0: TikTok giới hạn số lần nhập sai. Màn hình cảnh báo *"Còn 1 lần nhập. Hãy thử lại."* nếu cố nhập tiếp sẽ bị khóa đăng nhập tạm thời hoặc văng checkpoint danh tính.

## 3. Quy tắc khắc phục & Phòng ngừa (Invariant)
1. **Fail-Fast khi gặp "Sai tài khoản hoặc mật khẩu" / "Còn N lần nhập"**:
   - `drive_login_screens` / `wait_login_success` trong `tiktok_login_v1.py` BẮT BUỘC phải scan marker sai mật khẩu (`"sai tai khoan hoac mat khau"`, `"wrong password"`, `"con 1 lan nhap"`, `"con 2 lan nhap"`).
   - Khi phát hiện: DỪNG NGAY (Abort), thoát exit code đặc thù (e.g. exit 5 - `PASSWORD_INVALID_OR_LOCKED`), TUYỆT ĐỐI CẤM retry mù quáng hoặc treo chờ timeout 388s/600s.
2. **Không fallback mù sang reconcile_tiktok_accounts khi đã fail sai pass**:
   - Khi `fast_login` thất bại do `PASSWORD_INVALID_OR_LOCKED`, `feed_swipe_smoke.py` phải chặn ngay fallback `reconcile_tiktok_accounts.py` vì reconcile cũng dùng chung file Excel và sẽ tiếp tục nhập sai pass lần thứ 2 dẫn tới khóa nick.
3. **Luồng cứu hộ chuẩn cho Nick Passwordless**:
   - Chuyển sang đăng nhập bằng Email `gabrundozarache@hotmail.com` qua mã OTP Hotmail (đọc tự động qua XOAUTH2 IMAP).
   - Hoặc dùng Web Chrome vào `tiktok.com/login/email/forget-password` qua OTP Hotmail để đặt mật khẩu chuẩn theo cột D Excel, sau đó mới nạp vào app.
