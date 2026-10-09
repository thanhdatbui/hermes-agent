# Xử lý Onboarding Tiểu sử (Bio Screen) & Lỗi Lệch 2FA Authenticator sau Login

## 1. Màn hình Onboarding Tiểu sử (Bio Screen) sau khi đăng nhập TikTok
- **Dấu hiệu nhận biết**: Sau khi điền email/password và xác thực thành công, TikTok hiển thị màn hình *Tiểu sử / Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào*.
- **Vấn đề**: Script login cũ chỉ tìm các nút như *Bỏ qua*, *Xác nhận*, *Trang chủ*, dẫn tới bị kẹt vòng lặp `handle_post_auth_screens` do màn hình Bio có nút `Hủy` ở góc trái `[24,72][167,204]` (center 95, 138) hoặc `Lưu` ở góc phải.
- **Xử lý chuẩn**:
  - Nhận diện text `Tiểu sử` hoặc `Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào`.
  - Tự động tap `Hủy` / `Bỏ qua` (fallback coord `(95, 138)`) để đóng form Bio và vào thẳng Profile/Feed.

## 2. Triage & Xử lý khi mã 2FA Authenticator bị TikTok từ chối
- **Hiện tượng**: Tài khoản có secret 2FA TOTP trong Excel (`taikhoan_dat_v2_updated .xlsx`), sinh mã đúng thuật toán TOTP nhưng TikTok báo mã không hợp lệ sau 3 lần thử.
- **Nguyên nhân**:
  - Secret 2FA được sinh ra trong các batch add-2fa trước đó nhưng chưa được TikTok kích hoạt hoàn tất (bị hủy ở bước xác thực cuối).
  - Hoặc tài khoản đã chuyển phương thức xác thực sang Email OTP.
- **Giải pháp khôi phục**:
  - Không kết luận nick bị văng hay mất phiên.
  - Sử dụng cờ `--otp-only` (chuyển sang nhận mã OTP gửi về Email/Hotmail/Gmail) để login vào tài khoản.
  - Sau khi vào nick, truy cập *Cài đặt và quyền riêng tư -> Bảo mật -> Xác minh 2 bước* để cấu hình lại Authenticator App và cập nhật chuỗi Secret mới vào Excel.
