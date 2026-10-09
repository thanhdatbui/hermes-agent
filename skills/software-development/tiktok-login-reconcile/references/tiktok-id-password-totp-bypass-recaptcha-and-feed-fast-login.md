# TikTok ID + Password + 2FA TOTP Bypass Google reCAPTCHA & Feed Fast Auto-Login

## 1. Bẫy Email OTP & Google reCAPTCHA trên Farm (Anti-Pattern)
- **Hiện tượng**: Khi nạp nick TikTok bằng `login_email` (ví dụ `tranngan03012004@gmail.com`), TikTok bắt buộc gửi mã OTP 6 số về email.
- **Bẫy phát sinh**:
  1. Nếu máy chưa đăng nhập sẵn tài khoản Gmail đó, runner cố gắng thêm tài khoản Google vào Android (`android.settings.ADD_ACCOUNT_SETTINGS`).
  2. Server Google phát hiện đăng nhập thiết bị mới/IP proxy lạ $\rightarrow$ Kích hoạt checkpoint danh tính và bắt giải **reCAPTCHA hình ảnh** (chọn xe buýt, trụ cứu hỏa...).
  3. Quá trình giải reCAPTCHA tự động trên WebView Android cực kỳ thiếu ổn định, dễ bị Google từ chối *"Không thể xác minh tài khoản này là của bạn"*, gây treo hoặc fail cả lượt login.

---

## 2. Quy chuẩn Golden Path: TikTok ID + Password + 2FA TOTP
- **Nguyên lý cốt lõi**:
  - Khi tài khoản đã có sẵn `id` (TikTok username) và `tiktok_pass` trong tracking workbook (`taikhoan_dat_v2_updated .xlsx`), **BẮT BUỘC nhập TikTok ID thay vì Email**.
- **Luồng xử lý tối ưu**:
  1. Tại form đăng nhập TikTok ("Số điện thoại / Email / TikTok ID"), gõ TikTok username (`account["id"]`).
  2. TikTok nhận diện username $\rightarrow$ chuyển thẳng sang màn hình **Nhập mật khẩu** (`resource-id: f7l` / `text: Nhập mật khẩu`), hoàn toàn **KHÔNG phát OTP về email**.
  3. Gõ `account["tiktok_pass"]` $\rightarrow$ bấm *Tiếp tục* (`bounds=(540, 1681)`).
  4. Nếu tài khoản đã bật bảo mật 2 bước: TikTok hiển thị màn hình *Ứng dụng xác thực (Authenticator App)*.
  5. Runner lấy secret từ cột `twofa` trong Excel, tính mã TOTP 6 số bằng `pyotp.TOTP(secret.replace(' ', '').upper()).now()` và điền vào form.
  6. Vào thẳng trang chủ TikTok thành công trong 20–35 giây, **bỏ qua 100% Google reCAPTCHA và không cần mở app Gmail/Outlook**.

---

## 3. Fast Targeted Auto-Login trong Ca Nuôi (`feed_swipe_smoke.py`)
- **Vấn đề cũ**:
  - Khi mở Account Switcher trong ca nuôi mà không tìm thấy nick mục tiêu (`account-switcher-missing-expected`), hàm `_maybe_recover_missing_account_via_login` gọi `reconcile_tiktok_accounts.py --machines <M>`.
  - Script reconcile này quét toàn bộ 8 slot của máy, cố nạp tuần tự mọi nick thiếu trong Excel $\rightarrow$ Dễ chạm trần 8 nick, vướng nick thiếu pass hoặc bị timeout 300s–900s làm hỏng cả ca nuôi.
- **Giải pháp Fast Targeted Login mới**:
  - Ưu tiên gọi trực tiếp runner đơn lẻ:
    ```bash
    python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <machine_id> --email <expected_account> --ss
    ```
  - **Đặc tính kỹ thuật**:
    - Chỉ nạp đúng duy nhất nick mà ca nuôi đang cần (`expected_account`).
    - Thực thi với timeout ngắn 180s.
    - Đảm bảo `PYTHONPATH` được dọn sạch (`clean_env.pop("PYTHONPATH", None)`) và nạp `tools_path` động theo thư mục chứa `adb.exe`.
    - Khi lệnh kết thúc với exit code 0: `_maybe_recover_missing_account_via_login` trả về `True` ngay lập tức.
    - `verify_and_switch_profile` nhận tín hiệu thành công $\rightarrow$ Mở lại Switcher, chọn đúng nick vừa nạp và tiếp tục lướt feed bình thường.
    - Nếu Fast Path thất bại hoặc không tìm thấy file script: tự động fallback an toàn về `reconcile_script` ban đầu mà không làm crash flow.
