# Sign Out Everywhere & Account Takeover Verification (2026-08-22)

## 1. Bản chất của "Sign Out Everywhere" (Đăng xuất khỏi mọi nơi)
* Khi đổi mật khẩu Microsoft, các thiết bị cũ / app / trình duyệt khác có thể giữ session token/cookie hợp lệ lên đến 24 giờ.
* URL đích thực hiện: `https://account.live.com/proofs/manage/additional` (Tùy chọn bảo mật bổ sung).
* Marker hành động: Nút/Link *"Đăng xuất khỏi mọi nơi"* (`Sign out everywhere` / `Dang xuat khoi moi noi`).
* Thao tác xác nhận: Bấm nút xác nhận trong dialog cảnh báo 24 giờ $\rightarrow$ Microsoft hiển thị marker thành công: *"Chúng tôi đã bắt đầu đăng xuất cho bạn"* / *"Đã đăng xuất khỏi mọi nơi"*.

---

## 2. Quy trình chuẩn khi đổi mật khẩu & takeover hàng loạt
1. **Kiểm tra Preflight:** Xác nhận máy rảnh, serial khớp với workbook, `HOTMAIL_NEW_PASSWORD` và thông tin OTP IMAP sẵn sàng.
2. **Khôi phục / Đổi mật khẩu qua Chrome:** Gõ đầy đủ thông tin, vượt qua bước OTP gửi về `thanhdatbui1995@gmail.com`, đặt mật khẩu mới.
3. **Đồng bộ hóa dữ liệu tức thì:** Cập nhật ngay mật khẩu mới vào file Excel (`gmail_clean_v2.xlsx`), tạo file backup có timestamp.
4. **Sign Out Everywhere:** Mở trang bảo mật nâng cao và kích hoạt đăng xuất mọi thiết bị.
5. **Dọn dẹp & Khóa máy:** Tắt toàn bộ ứng dụng trên máy, đưa về HomeScreen và duy trì Device Lock nếu đang trong phiên bảo trì.
