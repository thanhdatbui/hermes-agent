# Gmail Account Switcher False-Match Inbox Security Email Pitfall

## Triệu chứng
Khi runner `tiktok_login_v1.py` cần lấy OTP từ Gmail và gọi quy trình switch account:
```text
[otp-gmail] Avatar fallback (985, 138)
[otp-gmail] Switch sang <target_email>
✓ tap (...) | text='Chưa đọc, , , Google, , Cảnh báo bảo mật quan trọng, , Google đã chặn nỗ lực đăng nhập <target_email> ...'
[otp-gmail] mailbox check after account switcher/1: pkg=com.google.android.gm selected=N inbox=N reason=no_inbox_marker acct=''
[otp-gmail] Chua o Gmail mailbox (after account switcher, reason=no_inbox_marker) -> mo Gmail inbox
```
Sau đó runner bị kẹt vô tận trong vòng lặp kiểm tra mailbox và timeout.

## Nguyên nhân gốc rễ
1. Khi mở Gmail để switch sang tài khoản đích, runner tap vào avatar để mở dialog / bottom sheet tài khoản Google.
2. Nếu dialog tài khoản chưa kịp mở hoặc bị đóng, hoặc matcher quét toàn bộ XML không giới hạn trong container dialog tài khoản (Google account switcher dialog / bottom sheet):
   - Trong hòm thư hiện tại thường có thư bảo mật của Google gửi về với tiêu đề:
     `"Cảnh báo bảo mật quan trọng, , Google đã chặn nỗ lực đăng nhập <target_email> Ai đó vừa dùng mật khẩu..."`
   - Node của hàng thư này chứa chuỗi `<target_email>`.
   - Hàm tìm kiếm account node quét trúng hàng thư này và ra lệnh tap vào tọa độ của nó thay vì chọn tài khoản trong dialog.
3. Khi tap trúng thư cảnh báo bảo mật:
   - Màn hình chuyển vào Activity xem chi tiết email cảnh báo (`com.google.android.gm`).
   - Màn hình chi tiết email không có các marker của danh sách hộp thư đến (`reason=no_inbox_marker`), tài khoản hiện hành không được chuyển đổi, và runner rơi vào vòng lặp chờ vô tận.

## Phòng tránh & Giải pháp chuẩn
1. **Kiểm tra trạng thái dialog trước khi match:** Phải đảm bảo dialog Google Account Switcher (`com.google.android.gms:id/...` hoặc container bottom sheet tài khoản) thực sự hiển thị trước khi quét tìm target email.
2. **Scoping node tìm kiếm:** Chỉ match `<target_email>` trên các node thuộc container chọn tài khoản hoặc có resource-id / class tương ứng với account picker (ví dụ: `account_display_name`, `account_name`, text view của item account trong dialog).
3. **Loại trừ thư inbox:** Tuyệt đối không match text `<target_email>` trên các node có chứa text đặc trưng của hàng thư như `"Chưa đọc"`, `"Đã đọc"`, `"Cảnh báo bảo mật"`, `"Google đã chặn"`, hoặc có parent là `conversation_list` / `RecyclerView` danh sách thư.
