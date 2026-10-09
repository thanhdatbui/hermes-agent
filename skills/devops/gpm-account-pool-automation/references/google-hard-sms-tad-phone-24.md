# Google Hard SMS Challenge & Số Điện Thoại Cá Nhân Tad (0906746624)

## Hiện tượng & Cơ chế Google Challenge
Khi đăng nhập tài khoản Google trên GPMLogin profile mới hoặc sau cooldown, Google có thể kích hoạt màn hình **Xác minh danh tính của bạn** với các tùy chọn:
1. `Nhận mã xác minh tại •••• ••• •24 (Số điện thoại khôi phục)`
2. `Nhận cuộc gọi đến số ••• ••• •24`
3. `Sử dụng một điện thoại hoặc máy tính khác để hoàn tất việc đăng nhập`

## Quy tắc bắt buộc
1. **Số điện thoại đuôi 24:**
   - SĐT đuôi `24` là số cá nhân của **Tad** (user): `0906746624`.
   - Khi Google bắt xác nhận đầy đủ số điện thoại trước khi gửi mã: điền chính xác `0906746624`, nhấn "Gửi", sau đó **dừng automation và hỏi user để lấy mã OTP 6 số**.
2. **Tránh bẫy Selector Input:**
   - Màn hình xác nhận SĐT dùng ô `input#phoneNumberId, input[name="phoneNumber"]`.
   - TUYỆT ĐỐI KHÔNG dùng `input[type="tel"]` chung cho cả ô xác nhận SĐT lẫn ô nhập OTP, vì khi Google chuyển sang màn hình nhập mã OTP 6 số, ô OTP cũng có thể là `type="tel"`, dẫn đến script lặp vô tận việc điền SĐT vào ô OTP!
3. **Cảnh báo Rate-Limit (Quá nhiều lần):**
   - Nếu màn hình báo dòng đỏ: `"Không khả dụng vì bạn đã thử quá nhiều lần. Vui lòng thử lại sau"`, tính năng SMS/Call của số đó đã bị Google rate-limit tạm thời.
   - **Xử lý:** Đưa tài khoản vào `cooldown_7days` trong `oauth_pipeline_status.json` để ngâm hạ nhiệt 24-48h. TUYỆT ĐỐI CẤM thử lại liên tục làm tài khoản bị checkpoint vĩnh viễn.
4. **Đường dẫn ảnh nghiệm thu gửi Telegram:**
   - Khi gửi ảnh qua cú pháp `MEDIA:<path>`, luôn copy ảnh ra thư mục phẳng không chứa khoảng trắng (ví dụ `C:/Users/Kibe/<name>.png`), tránh dùng đường dẫn chứa space như `D:/Taadaa/GPM auto/...` khiến Telegram client không parse và tải được ảnh.
