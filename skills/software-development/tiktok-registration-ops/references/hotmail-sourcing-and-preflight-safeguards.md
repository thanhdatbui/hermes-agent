# Hotmail / Outlook Sourcing & Preflight Safeguards (2026-09-19)

### 1. Tiêu chuẩn Mail Reg TikTok
- **BẮT BUỘC:** Hotmail / Outlook **ZIN, CHƯA QUA DỊCH VỤ / CHƯA QUA TIKTOK** (định dạng OAuth2 Microsoft Graph API full token + client_id + recovery_mail).
- **CẤM TUYỆT ĐỐI:** Không bao giờ mua hoặc đề xuất các mã sản phẩm có nhãn `"Hàng qua TikTok"`, `"Đã qua dịch vụ"` (ví dụ ID 57, ID 22874 trên BoxTaiKhoan) để dùng cho luồng đăng ký mới vì sẽ dính lỗi tài khoản đã tồn tại.

### 2. Chống Báo Cáo Ảo Cooldown Do Thiếu Mail
- Trong `ensure_row_accounts.py`, khi mua mail thất bại hoặc kho hết hàng (`buy_hotmail.py` trả về 0 mail), máy không chạy được là do **HẾT HÀNG / THIẾU MAIL**.
- **CẤM ngộ nhận gán nhãn `Cooldown`:** Chỉ phân loại là cooldown khi máy đã đăng ký thành công trong ngày hôm nay (`reg_today`) hoặc có lock cooldown thật. Máy bị trượt do thiếu mail phải được báo cáo đúng là thiếu mail / lỗi mua mail.

### 3. Exit Code Zero Trap Trong `buy_hotmail.py`
- Khi `buy_multiple_accounts` dừng sớm do hết hàng (`accounts_bought < count`), script mua mail phải báo lỗi `OUT_OF_STOCK` và thoát với mã lỗi `sys.exit(1)`.
- Tuyệt đối không thoát `exit code 0` khi số lượng mail nạp vào workbook là 0, tránh làm caller (`ensure_row_accounts.py`) ngộ nhận là đã mua mail thành công rồi tiếp tục gọi batch reg rỗng.

### 4. Bẫy Tồn Ảo Trên Sàn BoxTaiKhoan / CloneFBIG
- Bảng giá catalog API (`products.php`) có thể hiển thị còn hàng (ví dụ ID 129 hiển thị stock 10k), nhưng endpoint backend (`ajaxs/client/product.php`) có thể trả về lỗi `"Sản phẩm không tồn tại trong hệ thống"`.
- Luôn kiểm tra tính khả dụng thực tế của endpoint đặt hàng trước khi cập nhật ID sản phẩm mặc định.
