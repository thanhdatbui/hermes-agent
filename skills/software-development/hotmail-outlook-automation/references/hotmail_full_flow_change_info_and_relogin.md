# Full Flow Change Info Hotmail Khép Kín (2026-10-12)

## 1. Trình Tự Thực Thi 5 Bước Trong Cùng 1 Phiên Chạy
1. **Bước 1: Add Mail Khôi Phục & Xác Minh OTP**
   - Kiểm tra trang `account.live.com/proofs/manage/additional`.
   - Nếu tài khoản đã có sẵn mail khôi phục (hoặc thẻ "Gửi mã qua email" / "Email a code") -> BỎ QUA NGAY LẬP TỨC.
   - Nếu chưa có: Mở modal thêm phương thức -> Chọn "Gửi mã qua email" -> Điền `<clean_username><3rand>@fviainboxes.com` -> Bóc OTP qua API `fviainboxes.com/messages?username=...` -> Xác minh -> Cập nhật Cột 5 của `gmail_clean_v2.xlsx`.
2. **Bước 2: Thiết lập 2FA Authenticator App (TOTP) & Bật Công Tắc Tổng**
   - Mở modal thêm phương thức -> Chọn "Sử dụng ứng dụng" -> Chọn "Ứng dụng xác thực khác" -> Bóc Secret Key.
   - Dùng `pyotp.TOTP(secret).now()` điền mã xác nhận -> Kích hoạt 2FA TOTP.
   - Điều hướng tới `account.live.com/proofs/EnableTfa` để bấm hoàn tất bật công tắc tổng Two-step verification.
   - Lưu Secret Key vào Cột 4 của `gmail_clean_v2.xlsx`.
3. **Bước 3: Đổi Mật Khẩu Mới**
   - Điều hướng tới `account.live.com/password/change`.
   - Nhập mật khẩu hiện tại -> Điền mật khẩu mới (chuỗi ngẫu nhiên an toàn) -> Bấm Submit lưu mật khẩu.
4. **Bước 4: Đăng Xuất Khỏi Mọi Nơi (Sign Out Everywhere)**
   - Điều hướng về `proofs` -> Click link `#DeleteTrustedDevices`.
   - Bắt dialog modal xác nhận -> Bấm "Đăng xuất" / "Sign out" để hủy toàn bộ phiên cũ trên mọi thiết bị.
5. **Bước 5: Đăng Nhập Lại Bằng Pass Mới & Lưu Phiên Sống Trên GPM**
   - Điều hướng tới `login.live.com`.
   - Điền email -> Điền mật khẩu mới -> Nếu hỏi 2FA thì sinh TOTP điền vào.
   - Bắt màn hình KMSI ("Duy trì đăng nhập / Không hiển thị lại") -> Bấm "Có" để ghi session/cookies bền vững vào profile ổ đĩa.
   - Kiểm tra vào được Dashboard thành công -> Đóng GPM profile và chuyển stage sang `DONE`.

## 2. Quy Tắc Bảo Mật & Kinh Nghiệm Vận Hành (Pitfalls)
- **Quy tắc 2 Phương Thức:** Microsoft bắt buộc tài khoản phải có ít nhất 2 phương thức bảo mật hợp lệ (ví dụ: Mật khẩu + Mail khôi phục) thì mới cho phép bật 2FA Authenticator app. Tài khoản Zin trắng (chỉ có pass) bắt buộc phải add mail khôi phục trước rồi mới add 2FA.
- **Không Cần Ngâm Thêm:** GPM Profile và IP Proxy chỉ cần ngâm 7 ngày ban đầu (`WAIT_7D`) để thành Trusted Device. Khi add mail khôi phục dạng thêm mới (Add additional), Microsoft kích hoạt ngay lập tức có tích xanh "Cập nhật", không bị dính 30 ngày Security Hold. Do đó, ĐƯỢC PHÉP add 2FA và đổi pass LIỀN trong cùng 1 lần chạy, TUYỆT ĐỐI KHÔNG cần ngâm thêm 7 ngày.
- **Interstitial Guard:** Khi xử lý các màn hình điều khoản chuyển tiếp (`handle_microsoft_interstitials`), phải kiểm tra nếu URL chứa `proofs` thì bỏ qua việc click các nút "Tiếp theo", tránh click nhầm vào nút của form chính khi đang mở modal.
- **Đóng Tab CDP:** Đóng tab trên Chrome CDP (`GET /json/close/{target_id}`) chỉ giải phóng RAM render, hoàn toàn không làm mất cookie/phiên của profile GPM.
