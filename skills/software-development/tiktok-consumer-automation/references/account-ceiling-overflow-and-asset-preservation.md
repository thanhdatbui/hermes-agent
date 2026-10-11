# Kỷ Luật Bảo Toàn Tài Sản Khi Chạm Trần 8 Nick & Điều Phối Nick Dư (11/10/2026)

## 1. Bản chất sự cố Tràn Trần 8 Nick (Account Ceiling Overflow)
- **Cơ chế giới hạn của TikTok**: App TikTok trên Android chỉ cho phép lưu phiên đăng nhập tối đa 8 tài khoản cùng lúc trong Switcher.
- **Nguyên nhân dồn thừa nick**: Khi hệ thống chạy reg bù mở rộng ca hoặc thay nick lỗi, script chỉ bấm "Thêm tài khoản khác" mà không kiểm tra số nick thực tế đang lưu trong app.
- **Quy tắc bảo toàn tài sản**: MỌI nick đang đăng nhập sống trên máy đều là tài sản farm. CẤM gọi là "kí sinh" và CẤM tự tiện logout/xóa bỏ tài khoản để lấy chỗ.

## 2. Quy trình điều phối chuẩn
1. **Khảo sát Switcher**: Đọc danh sách tài khoản thực tế đang có trên thiết bị, đối soát với workbook của máy.
2. **Map lại nick có sẵn vào máy**: Giữ lại nick đang sống trong máy, map chính thức vào slot phù hợp trên Excel (`TikN.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`, SQLite).
3. **Xác định nick non nhất để điều phối sang máy thiếu slot**: Tìm nick non nhất (dựa trên ngày reg, video đã up, follower) để chuyển sang máy còn trống slot (< 8 tài khoản, ví dụ cụm Admin M266).
4. **Bắt buộc Bật 2FA & Đặt Password TRƯỚC KHI chuyển**: Chạy Phase B 2FA trên máy nguồn, đặt mật khẩu và bật 2FA TOTP, lưu Secret Key + Pass vào workbook trước khi logout.
5. **Ghi sổ máy nhận trước — TUYỆT ĐỐI CHƯA vội login**: Điền đầy đủ thông tin nick non vào các file Excel của máy nhận, chỉ ghi sổ sách, KHÔNG tự tiện login ngay lên thiết bị nhận. Sau đó logout nick non khỏi máy nguồn để giải phóng slot và login nick chính chủ còn lại.
