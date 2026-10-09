# Nguồn Hotmail Graph API & Lưu ý mua mail sàn dongvanfb.net

## 1. Phân loại sản phẩm Hotmail trên dongvanfb.net
Sàn `dongvanfb.net` cung cấp các loại tài khoản Hotmail/Outlook xuất định dạng kèm token OAuth2 (350đ/mail), nhưng phân quyền (scope) của token giữa các loại rất khác nhau:

| ID trên sàn | Tên sản phẩm | Token Scopes / Quyền Graph API | Đánh giá sử dụng Farm |
| :---: | :--- | :--- | :--- |
| **5** | `Hotmail TRUSTED [GRAPH API]` | **Chỉ có IMAP/POP3/SMTP**, KHÔNG có `Mail.Read` | ❌ **LỎ - KHÔNG DÙNG ĐƯỢC**: Gọi Microsoft Graph API (`graph.microsoft.com/v1.0/me/messages`) bị báo lỗi `Graph token invalid`. Muốn đọc OTP phải mở app Outlook trên thiết bị gõ pass thủ công, dễ dính checkpoint. |
| **59** | `Hotmail TRUSTED [IMAP/POP3/GRAPH API]` | Tương tự ID 5, chỉ mở cổng IMAP cho tool nuôi giả lập cũ | ❌ **KHÔNG DÙNG**: Không hỗ trợ đọc trực tiếp qua Graph API PC. |
| **57** | `HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` | **Full scopes**: `User.Read`, `Mail.ReadWrite`, `Mail.Read`, `IMAP`, `POP`, `SMTP` | ✅ **CHUẨN 100%**: Microsoft Graph API đọc OTP trực tiếp từ PC mượt mà. |

## 2. Quy trình ngâm 7 ngày & chiếm quyền sở hữu độc quyền (ID 57)
Loại ID 57 được gán sẵn mail khôi phục phụ dạng `@fviainboxes.com`. Để sử dụng an toàn lâu dài cho Farm:
1. **Giai đoạn Reg & Nuôi (Ngày 1 - 7):** Dùng token OAuth2 để đọc OTP từ xa qua PC, không cần login trình duyệt/app Outlook.
2. **Sau 7 ngày ngâm nick:**
   - Đăng nhập tài khoản Microsoft trên trình duyệt.
   - Đổi mật khẩu mới, tích chọn **"Sign me out of all devices"** (Đăng xuất khỏi tất cả các thiết bị) để đá toàn bộ phiên cũ của shop ra ngoài.
   - Vào *Security / Advanced Security Options*, bấm gỡ bỏ (remove) email khôi phục `@fviainboxes.com`.
   - Thêm email khôi phục hoặc số điện thoại riêng của Farm. Tài khoản trở thành sở hữu độc quyền vĩnh viễn.

## 3. Lưu ý về nhãn "Chưa qua TikTok"
- Trên `dongvanfb.net` hoàn toàn **không có nhãn "Chưa qua dịch vụ" hay "Chưa qua TikTok"** (tệp khách của sàn chủ yếu là Via/Clone Facebook).
- Không được shop cam kết bao Zin TikTok như CloneFBIG hay BoxTaiKhoan. Khi mua nên mua theo đợt vừa phải để kiểm tra chất lượng lô mail.

## 4. Kỷ luật tra cứu Source of Truth trước khi test & Chống tạo Nick Ký Sinh (23/09/2026)
- **Tra cứu trạng thái trước khi test**: BẮT BUỘC kiểm tra `taikhoan_dat_v2_updated .xlsx`, `tiktok_tracker.db` và `social_reg_log.txt` xem email đã được Farm đăng ký chưa trước khi mang đi test lại. Tránh tình trạng Farm đã tự động reg thành công từ trưa mà Coordinator không biết lại đem đi test lại.
- **Khi TikTok hiện "Bạn đã đăng ký"**: DỪNG LẠI NGAY. CẤM tự ý bấm Tiếp tục rồi nhập OTP để login sang máy khác. Việc login nick đã có trên Máy A sang Máy B sẽ tạo thành Nick Ký Sinh (1 tài khoản đăng nhập song song trên 2 thiết bị khác nhau), dẫn đến nguy cơ bị TikTok quét hành vi bất thường và khóa tài khoản.
