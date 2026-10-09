# Quy trình Phục hồi Tài khoản Gmail lên GPMLogin sau khi Bị Revoke OAuth

## 1. Bản chất: Revoke Token ≠ Tài khoản DIE
- Lỗi `invalid_grant: Refresh token rejected`: Google thu hồi token của App Antigravity (hết hạn 6 tháng, đổi IP proxy di động hoặc đổi mật khẩu).
- Tài khoản Gmail trên GPM profile có thể vẫn còn sống hoặc chỉ bị văng session đăng nhập trên Chrome. Tuyệt đối không xóa nick khỏi Excel khi chưa kiểm tra.

## 2. Quy tắc Sống còn: BẮT BUỘC Check-live trước khi Login lại
- Chạy check live tài khoản bằng runner `run_checkmail_kibe_farm.py` (checkmail.live qua mobile proxy Farm có Turnstile solver).
- Tuyệt đối không chạy script login vào các tài khoản DIE / BAN / SUSPENDED hoặc Phone Checkpoint (`challenge/iap`) vì sẽ làm nghẽn worker và hỏng trust score của IP proxy.

## 3. Xử lý Profile Trắng Session vs Profile Còn Session
- **Còn session Google**: Có thể chạy Silent OAuth (mở authUrl -> Account Chooser -> Allow). Timeout chờ trên proxy 4G phải >= 60s - 90s.
- **Mất session Google (Trắng cookies)**: Silent OAuth sẽ timeout. Bắt buộc kích hoạt pipeline login đầy đủ (`run_oauth_s7_pipeline.py`):
  1. Nhập Password từ Excel.
  2. Giải 2FA TOTP qua `pyotp` (lấy từ cột `2FA_Secret`).
  3. Điền recovery email nếu gặp challenge.
  4. Giải reCAPTCHA / Audio challenge nếu xuất hiện.
  5. Bắt mã xác nhận Google Prompt trên máy Samsung S7 qua ADB.
  6. Lưu mật khẩu vào Chromium Preferences rồi mới hoàn tất OAuth exchange.

## 4. Kiểm tra Tuổi Ngâm An toàn (>= 7 ngày)
- Không lấy nhầm cột "Cập Nhật" trong `master_gmail_manager.xlsx` (ngày checklive) để tính tuổi tài khoản.
- Lấy ngày tạo gốc từ file `gmail_clean_v2.xlsx` (cột 'ngày tạo' / 'ngày sinh').
