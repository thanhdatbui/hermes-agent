# Quy trình Khôi phục và Nạp lại Pool Tài khoản khi Google OAuth Revoke

## 1. Bản chất giữa "Google OAuth Revoke" và "Tài khoản Die"
- **Revoked Token (`invalid_grant: Refresh token rejected`)**: Chỉ là phiên ủy quyền của ứng dụng Antigravity trên Google Cloud Console bị thu hồi (do token hết hạn 6 tháng, đổi IP mạng, hoặc ứng dụng bị gỡ liên kết).
- **Tài khoản Gmail vẫn có thể LIVE**: Cần đối chiếu với `gmail_clean_v2.xlsx` hoặc `master_gmail_manager.xlsx`. Không được vội vã kết luận nick đã chết hay xóa vĩnh viễn profile khi chưa checklive.

## 2. Nguyên tắc An toàn: Check-live trước khi Login lại
- **Cấm đoán mò mẫm**: Trước khi chạy bất kỳ script login hay re-auth nào lên GPM, **BẮT BUỘC** phải chạy check live tài khoản Gmail qua engine `checkmail.live` (`run_checkmail_kibe_farm.py`).
- Không được phép cố đăng nhập các tài khoản đã bị DIE / BAN / SUSPENDED hoặc Phone Checkpoint (`challenge/iap`) vì sẽ làm bẩn dải IP proxy mobile và nghẽn hàng đợi đăng nhập.

## 3. Phân biệt Silent OAuth vs Interactive Login trên GPMLogin
1. **Silent OAuth (Chỉ có tác dụng khi profile đã có sẵn Session Google)**:
   - Profile Chromium đang lưu sẵn login cookies của Google.
   - Script chỉ cần mở `authUrl`, chọn tài khoản từ Account Chooser và click nút "Cho phép" / "Tiếp tục".
   - Timeout cho mạng proxy 4G xoay vòng phải tối thiểu 60s - 90s (cấm để 35s gây ngắt giữa chừng).
2. **Interactive Login (Khi Profile bị văng session trắng tinh)**:
   - Khi profile bị logout hoàn toàn (`myaccount.google.com` redirect về landing page), luồng Silent OAuth sẽ thất bại và bị kẹt ở ô nhập Email/Password.
   - Bắt buộc phải kích hoạt pipeline login đầy đủ (`run_oauth_s7_pipeline.py`):
     - Điền Email + Mật khẩu.
     - Tự động sinh và điền TOTP 2FA (từ `2FA_Secret` trong Excel).
     - Điền Recovery Email nếu có challenge.
     - Giải reCAPTCHA / Audio challenge.
     - Bắt mã xác nhận Google Prompt trên thiết bị Android S7 qua ADB.
     - Sau khi login thành công, lưu mật khẩu vào Chromium Preferences và mới tiến hành exchange OAuth code về OmniRoute.

## 4. Kiểm tra Tuổi Ngâm Tài khoản (Age Check)
- Khi lọc candidate để login, cấm lấy nhầm cột "Cập Nhật" (ngày checklive gần nhất) làm ngày tạo khiến tài khoản bị hiểu nhầm là 0 ngày tuổi.
- Bắt buộc tra cứu ngày tạo gốc từ file nguồn `gmail_clean_v2.xlsx` (cột 'ngày tạo' hoặc 'ngày sinh') để đảm bảo tài khoản đã đủ ngâm an toàn >= 7 ngày.
