# Chu Trình Cuốn Chiếu Vòng Đời Profile GPM: Login Đêm ↔ Bật 2FA Sáng

## 1. Kiến trúc phân tách hai ca (Decoupled Two-Phase Architecture)
Hệ thống tự động hóa Gmail trên GPM hoạt động theo nguyên tắc cuốn chiếu tuần tự giữa hai ca để tránh xung đột tải và đảm bảo an toàn tuyệt đối cho session:

1. **Ca Đêm (21:30 - 23:45)**: `post-evening-gpm-login-watchdog`
   - Quét các profile GPM mới tạo hoặc profile chưa có session Google (hoặc cần hồi sinh).
   - Mở profile qua GPM Local API (:19995), tự động đăng nhập tài khoản Google bằng password chuẩn từ Excel (`master_gmail_manager.xlsx` / `gmail_clean_v2.xlsx`).
   - Xử lý các challenge đăng nhập (chỉ khi có 2FA_Secret hoặc phương thức xác minh qua máy S7 nếu cần).
   - Lưu session cookie an toàn trong profile GPM.

2. **Ca Sáng (08:30 - 11:30)**: `post-morning-gmail-2fa-watchdog`
   - Chạy sau khi Ca 1 nuôi feed hoàn thành (`feed_session_reported.json` báo xong).
   - Quét các profile GPM có Gmail + password nhưng cột 2FA còn trống.
   - Mở profile qua CDP, kiểm tra `myaccount.google.com`:
     - Nếu profile đã có session hợp lệ: điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator`, bóc Secret Key Base32, kích hoạt 2FA.
     - Nếu gặp `NO_SESSION` (redirect về `https://www.google.com/account/about` hoặc trang login): **CHỦ ĐỘNG BỎ QUA**, ghi nhận vào state/log để bàn giao lại cho Ca Đêm.
   - Khi kích hoạt thành công: cập nhật đồng bộ Secret Key vào cả hai file:
     - `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Master_All` & `Kibe_Farm_S7`)
     - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`

## 2. Xử lý Trạng thái `NO_SESSION`
- **Hiện tượng**: Watchdog sáng báo `NO_SESSION - Profile chưa đăng nhập Google (redirect về https://www.google.com/account/about/?hl=vi)`.
- **Nguyên nhân**: Profile mới được tạo từ watchdog sync lifecycle (`sync_gpm_lifecycle.py`), chưa trải qua quy trình login ban đầu.
- **Biện pháp điều phối**:
  - Không coi đây là lỗi hỏng hóc khẩn cấp.
  - Tuyệt đối không tự ý kích hoạt login đột ngột trong giờ nuôi feed ban ngày nếu chưa tới khung giờ cho phép.
  - Để watchdog ca tối (`post-evening-gpm-login-watchdog`) tự động thực hiện login, sau đó sáng hôm sau watchdog 2FA sẽ tự động hoàn tất khâu kích hoạt.
