# TikTok Registration Error Reporting & Password Policy

## 1. Quy tắc báo cáo lỗi máy & Chụp ảnh
- Khi máy gặp lỗi trong quá trình reg/login, bắt buộc chụp màn hình máy bị lỗi.
- **Vẽ banner đỏ ở đầu ảnh:** Tương tự cơ chế `send_farm_machine_alert` của `automation_core` / `ai_recovery`:
  - Kích thước banner: chiều cao khoảng 5% chiều cao ảnh.
  - Màu nền: Đỏ `(220, 20, 60)`.
  - Chữ hiển thị: `[MAY XX] - HH:MM DD/MM` (chữ trắng in hoa rõ ràng).
- Gửi ảnh qua cú pháp: `MEDIA:<path>` trên một dòng riêng biệt, không bọc markdown.
- Kèm thông tin số máy `[MÁY XX]` và giải thích nguyên nhân bằng **tiếng Việt ngắn gọn, dễ hiểu**; không copy paste khối log tiếng Anh thô.

## 2. Quy tắc quản lý Password trong Excel
- Đối với flow đăng ký qua OTP / email-only của TikTok mà **không xuất hiện màn hình nhập password**:
  - Trong workbook `taikhoan_dat_v2_updated .xlsx` (cột D / PASS), **BẮT BUỘC ĐỂ TRỐNG (`None`)**.
  - **TUYỆT ĐỐI CẤM** tự sinh mật khẩu ngẫu nhiên để điền vào excel khi app không yêu cầu nhập pass (để sau này vào TikTok thiết lập mật khẩu thủ công).
- Chỉ điền password vào Excel khi flow thực sự yêu cầu nhập mật khẩu trên giao diện app và script đã nhập thành công.

## 3. Quy tắc quản lý Device Lock
- Chỉ nhả lock thiết bị khi đăng ký **SUCCESS** (đã ghi nhận tracking và dọn dẹp app về Home).
- Các máy **FAILED / DỪNG HIỆN TRƯỜNG**: Bắt buộc giữ nguyên device lock ở trạng thái `blocked` để bảo vệ hiện trường và tránh các luồng/cron khác can thiệp.
