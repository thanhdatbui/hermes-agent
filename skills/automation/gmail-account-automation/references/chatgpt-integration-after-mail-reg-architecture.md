# Kiến Trúc Nối Đăng Ký ChatGPT Sau Khi Reg Mail / Hotmail

## 1. Cơ Sở & Đánh Giá Tính Hợp Lý
- **Ưu điểm vượt trội của Hotmail đối với ChatGPT**:
  - Không bị Google checkpoint danh tính (`challenge/iap` đòi hỏi số điện thoại SMS).
  - OpenAI bắn thẳng mã OTP 6 số về hộp thư Microsoft Outlook.
  - Trên dàn máy Samsung S7 của Farm Taadaa, App Outlook (`com.microsoft.office.outlook`) đã được cài đặt và quản lý session sẵn.
  - Việc liên kết ChatGPT ngay sau khi tài khoản mail sống tạo ra tài khoản "trâu", tăng trust score và hình thành cụm tài khoản có đầy đủ định danh (TikTok + Mail + ChatGPT).

## 2. Điểm Kỹ Thuật Khi Nối Vào Luồng Hotmail / TikTok Reg
1. **Phân nhánh Client nhận OTP**:
   - Nếu email là `@gmail.com`: Mở App Gmail (`com.google.android.gm/.ConversationListActivityGmail`), vào mục *"Tất cả hộp thư đến"* (`[216,323][888,388]` -> tâm `540, 355`), vuốt kéo làm mới để lấy OTP.
   - Nếu email là `@hotmail.com` / `@outlook.com`: Mở App Outlook (`com.microsoft.office.outlook`), đọc danh sách thư mới nhất để trích xuất 6 số OTP.
2. **Kỷ luật trình duyệt Chrome trên S7**:
   - Trước khi gọi `register_chatgpt_on_device`, cần đảm bảo Chrome không bị đè popup Smart Lock / First Run bằng cách dismiss `"Sử dụng mà không cần tài khoản"` hoặc chạy qua môi trường sạch.
   - Luôn tạm thời freeze/stop các app có khả năng nhảy popup ngầm (như TikTok Policy update dialog) để tránh chiếm quyền focus của Chrome.
3. **Vị trí tích hợp trong hệ thống**:
   - **Tiktok_Reg (Luồng tạo nick)**: Gọi hook ngay sau khi `tiktok_reg_live_email_v1.py` xác nhận tạo nick thành công và lưu metadata.
   - **Hotmail Flow**: Gọi hook sau khi xác thực Hotmail sống hoặc đổi mật khẩu hoàn tất trên thiết bị.
