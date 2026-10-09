# TikTok Registration Server-Side Underage Lock & DatePicker Guard (2026-09-19)

## 1. Hiện tượng & Vấn đề thực tế (Máy 80)
- Khi reg tài khoản TikTok mới bằng Hotmail OAuth2 (`skulskischradle6402@hotmail.com`), hệ thống đã kết nối Graph API và điền OTP thành công vào TikTok.
- Tại màn hình chọn Ngày sinh (**"Ngày sinh của bạn là ngày nào?"**), do DatePicker dạng NumberPicker trên Samsung S7 (Android 7) bị cuộn không kiểm soát hoặc mặc định chạm mốc năm **2015** (<13 tuổi), TikTok lập tức hiện thông báo chặn:
  > *"Rất tiếc, có vẻ như bạn không đủ điều kiện tham gia TikTok... Nhưng cảm ơn vì đã đến với chúng tôi!"*
- Khi cố gắng đăng ký lại từ đầu với cùng email đó, dù đã cuộn năm sinh về đúng **1999** (27 tuổi) và nhập OTP mới, TikTok server vẫn trả về cùng popup từ chối trên.

## 2. Root Cause (Cơ chế bảo mật TikTok)
- **Server-Side Permanent Underage Flag**: Theo chính sách tuân thủ COPPA / bảo vệ trẻ vị thành niên của ByteDance, một khi địa chỉ email đã từng gửi request xác nhận ngày sinh dưới 13 tuổi trong một phiên đăng ký, server TikTok sẽ gắn cờ đen vĩnh viễn cho email đó.
- Khi email đã bị gắn cờ "không đủ điều kiện", toàn bộ các lượt đăng ký sau đó (kể cả chọn năm sinh hợp lệ >18 tuổi) đều bị reject tại bước submit ngày sinh. Email này trở thành phế phẩm (không thể dùng để tạo tài khoản TikTok nữa).

## 3. Quy tắc phòng vệ & Giải pháp (Structural Guards)
1. **Kiểm tra DatePicker trước khi Submit (Hard Pre-Submit Validation)**:
   - Trong `fill_birthday()` của `social_reg_v1.py`, TUYỆT ĐỐI KHÔNG được click nút **"Tiếp tục"** nếu chưa parse text ngày tháng hiển thị trên UI (`resource-id` hoặc TextView chứa text ngày sinh, ví dụ `19 tháng 9, 2015`).
   - Phải có logic assert regex năm sinh: `year <= 2005` (đảm bảo tuổi >= 21). Nếu năm > 2005, bắt buộc tiếp tục vuốt bánh xe năm (`swipe down`) cho đến khi năm sinh hiển thị lọt vào khoảng `1990 - 2002`.
2. **Xử lý khi dính cờ Underage**:
   - Khi phát hiện popup `"không đủ điều kiện tham gia TikTok"` / `"not eligible"`:
     - Lập tức dừng phiên của email hiện tại, đánh dấu email này là `DEAD_UNDERAGE` trong kho mail.
     - KHÔNG cố gắng retry đăng ký lại email này nhiều lần gây tốn OTP và cạn timeout.
     - Đưa máy về Home, thay thế bằng một email Hotmail Zin khác chưa từng bị dính cờ.
