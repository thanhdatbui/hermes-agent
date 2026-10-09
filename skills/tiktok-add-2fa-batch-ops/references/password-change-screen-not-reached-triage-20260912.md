# Triage & Fail-safe: PASSWORD_CHANGE_SCREEN_NOT_REACHED (12/09/2026)

## Bối cảnh Sự cố (Máy 43 / Row 338)
- **Chuông báo động Farm Alert:**
  ```text
  Phase 3 (Add 2FA TikTok) thất bại (exit_code=4): 43 | 338 | m************* | failed | PASSWORD_CHANGE_SCREEN_NOT_REACHED
  ```
- **Hiện trường thực tế:**
  + Máy 43 (serial `ce031603d3fb483904`).
  + Tài khoản: `minh.minh.chu7`, row 338 trong workbook `taikhoan_dat_v2_updated .xlsx`.
  + Kiểm tra Journal DPAPI (`5d417f6012e7872c71586f2bd249381bfed06f67aad426cd3baca8b3eeb82b6b.dpapi`): state là `EMAIL_DISABLED`, secret là `ASRXH7ME4VTNQO7WI57XDYU6BYDY7IXT`.
  + Kiểm tra ô E338 Excel: ĐÃ GHI `ASRXH7ME4VTNQO7WI57XDYU6BYDY7IXT`.
  + Kết luận: **2FA Authenticator đã được kích hoạt và lưu hoàn tất 100%!**

## Nguyên nhân Gốc rễ (Root Cause)
1. Sau khi bật xong Authenticator và tắt Email phụ, Phase B gọi thao tác phụ `ensure_password_saved=adapter.ensure_account_password_saved`.
2. Theo quy tắc 25/08/2026, các mật khẩu dạng legacy farm (như `Chaudang1112@`) thỏa mãn `password_needs_rotation() == True`, nên adapter cố gắng điều hướng ra menu ngoài để đổi mật khẩu sang chuỗi sinh ngẫu nhiên mạnh.
3. Trong `ensure_account_password_saved()`, adapter loop 8 lần để nhấn `KEYCODE_BACK` lùi từ màn `Bảo mật & quyền` ra `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Thông tin tài khoản` -> `Mật khẩu` -> `Thay đổi mật khẩu`.
4. Tuy nhiên, nếu TikTok đổi luồng giao diện, hiện popup hoặc kẹt màn hình sau 8 lần Back không tìm thấy form đổi pass, code cũ ném ngoại lệ:
   ```python
   raise LiveAdapterError("PASSWORD_CHANGE_SCREEN_NOT_REACHED")
   ```
5. Ngoại lệ này làm crash tiến trình worker, khiến batch runner đánh giá phiên chạy là `failed` và bắn Farm Alert đỏ chuỗi đêm (exit code 4), dù thực tế mục tiêu quan trọng nhất là **Bật 2FA** đã thành công mỹ mãn.

## Giải pháp & Fail-Safe Contract
- Thao tác đổi mật khẩu (`ensure_account_password_saved`) chỉ là bước gia tăng độ bảo mật phụ trợ ("nhân tiện đang trong settings"), **KHÔNG ĐƯỢC PHÉP ĐÁNH SẬP** toàn bộ kết quả bật 2FA đã hoàn tất.
- Khi hết 8 lần thử mà không tới được màn đổi mật khẩu:
  + Ghi log cảnh báo `[WARN] PASSWORD_CHANGE_SCREEN_NOT_REACHED: could not navigate to password change screen; retaining existing password`.
  + `return` an toàn thay vì ném exception.
  + Mật khẩu hiện tại trong workbook (vẫn hợp lệ) được giữ nguyên, bảo toàn trạng thái hoàn tất của nick và không gây sập batch Chuỗi Đêm.
