# TikTok Linked Email Verification & Live Inventory Rules

## 1. Live Inventory vs Tracking Workbook Policy
- `gmail_clean_v2.xlsx` là **KHO MAIL LIVE**, không phải file tạm xoá sau khi reg.
- Khi reg TikTok thành công:
  - Bảng tracking `taikhoan_dat_v2_updated .xlsx` **BẮT BUỘC ghi ID TikTok cùng hàng với Email gốc** đã reg (hoặc email đã link).
  - Không tự ý xoá mail khỏi `gmail_clean_v2.xlsx` chỉ vì đã reg xong.
- Khi chạy check-live / cleanup phát hiện mail die / mất khỏi máy:
  - Nếu **chưa có ID TikTok** trong tracking: Xoá khỏi `gmail_clean_v2.xlsx` để tránh tool detect bốc lại làm target reg.
  - Nếu **đã có ID TikTok** trong tracking: **GIỮ LẠI trong tracking**, ghi nhận ID TikTok và kiểm tra thực tế trên app.

## 2. Cách kiểm tra Email thực tế đang liên kết trên TikTok app
Khi có nghi vấn lệch mapping giữa workbook và app (data drift), kiểm tra trực tiếp trên app:
1. Mở TikTok -> vào tab **Hồ sơ** (Profile).
2. Nếu có nhiều nick trên máy, bấm vào tên tài khoản ở header trên cùng để mở popup **Chuyển đổi tài khoản** -> chọn đúng nick cần check.
3. Bấm **Menu 3 gạch** ở góc trên phải -> chọn **Cài đặt và quyền riêng tư** (Settings and privacy).
4. Chọn **Tài khoản** (Account) -> **Thông tin tài khoản** (Account information).
5. Đọc trường **Email**: hiển thị dạng mask `b***9@hotmail.com` hoặc email đầy đủ, đối chiếu chính xác với workbook.

## 3. Lọc Package System UI trong XML Dump (UI Parsing)
- UI XML dump từ Android (`uiautomator`) thường chứa lẫn các node của `com.android.systemui` (ví dụ: thông báo Google Play "Yêu cầu đăng nhập", "Không có điện thoại nào").
- Mọi hàm kiểm tra text/modal/button TikTok **BẮT BUỘC lọc theo `APP_PACKAGE = "com.ss.android.ugc.trill"`** qua `_iter_package_nodes()` hoặc `_package_flat_text()`, tuyệt đối không đọc phẳng toàn bộ XML hệ thống để tránh false positive.
