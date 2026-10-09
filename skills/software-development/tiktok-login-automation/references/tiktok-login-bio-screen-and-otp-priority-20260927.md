# Triage & Workarounds: TikTok Login Flow & 2FA Traps (2026-09-27)

## 1. Màn hình Onboarding Tiểu sử (Bio Screen Dismiss)
- **Hiện tượng**: Sau khi đăng nhập thành công một tài khoản mới/cũ, TikTok có thể điều hướng vào màn hình "Tiểu sử" (Bio screen) hiển thị:
  `Tiểu sử`, `Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào.`, nút `Hủy` ở góc trên bên trái `[24,72][167,204]` và `Lưu` ở góc trên bên phải.
- **Giải pháp**:
  - Trong `handle_post_auth_screens()` của `social_reg_v1.py`, nhận diện từ khóa `tieu su`, `chinh sua tieu su` hoặc `tv_header_bio`.
  - Tự động tap `Hủy` / `Bỏ qua` (tọa độ fallback `(95, 138)`) để vượt qua màn này vào thẳng Profile/Feed.

## 2. Bẫy Nhận Nhầm Màn Hình OTP thành Màn Hình Mật Khẩu (Force OTP Priority Trap)
- **Vấn đề**:
  - Trên màn hình nhập mã OTP xác minh của TikTok, luôn có liên kết nhỏ ở dưới là `Đăng nhập bằng mật khẩu`.
  - Khi vòng lặp `drive_login_screens()` kiểm tra `PASSWORD_HINTS` trước `OTP_HINTS`, chuỗi `mat khau` xuất hiện trên màn hình OTP sẽ khiến hệ thống nhận nhầm đây là màn hình nhập mật khẩu.
  - Hậu quả: Dù truyền cờ `--otp-only`, script vẫn cố điền mật khẩu, dẫn tới lỗi sai mật khẩu lặp lại và bị khóa đếm lùi lần thử.
- **Giải pháp**:
  - Khi `force_otp = True` (hoặc cờ `--otp-only`), BẮT BUỘC ưu tiên kiểm tra `OTP_HINTS` trước `PASSWORD_HINTS`.
  - Bỏ qua việc tap sang "Đăng nhập bằng mật khẩu" khi người dùng/hệ thống đã chỉ định luồng OTP.

## 3. Rà Soát Secret 2FA Farm (Base32 vs Backup Codes)
- **Thực tế**:
  - Đa số (99%) secret 2FA trong `taikhoan_dat_v2_updated .xlsx` là chuỗi TOTP Base32 32 ký tự.
  - Các ô có chuỗi dạng `xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx` (8 cụm 4 ký tự) là **Backup Recovery Keys**, không phải TOTP secret. Không thể dùng hàm TOTP chuẩn để sinh mã 6 số từ chuỗi này.
- **Hướng xử lý**: Với tài khoản sai/hỏng 2FA Authenticator, đăng nhập bằng luồng OTP gửi về Email chính chủ (đã qua cổng `checkmail.live`), sau đó vào Settings của TikTok để thiết lập lại Authenticator 2FA mới.
