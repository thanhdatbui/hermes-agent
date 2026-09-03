# Live Mail Inventory vs Tracking Management Rules

1. **Định nghĩa vai trò file dữ liệu:**
   - `gmail_clean_v2.xlsx`: **Kho mail live** (chứa toàn bộ mail đang sống trên hệ thống/máy), KHÔNG phải danh sách tạm để reg xong là xoá.
   - `taikhoan_dat_v2_updated .xlsx`: **Bảng tracking tổng hợp** tài khoản TikTok theo từng máy/slot.
   - Khi một mail đăng ký thành công TikTok, trong `taikhoan_dat_v2_updated .xlsx` **BẮT BUỘC ghi ID TikTok cùng hàng với Email gốc** tương ứng.

2. **Quy tắc dọn dẹp khi Check-live / Mail chết:**
   - Nếu mail die và **chưa có ID TikTok** trong tracking: Xoá khỏi `gmail_clean_v2.xlsx` để các script reg không bốc lại làm target.
   - Nếu mail die nhưng **đã có ID TikTok** trong tracking: **GIỮ LẠI hàng trong tracking**, kiểm tra xác thực thực tế trên app trước khi quyết định thay thế info.

3. **Quy trình xác minh Email thực tế liên kết với TikTok:**
   - Không chỉ dựa vào ghi chú workbook khi có data drift.
   - Vào app TikTok trên máy -> Hồ sơ -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> Tài khoản -> Thông tin tài khoản -> Đọc chính xác email (hoặc mask) đang liên kết.
