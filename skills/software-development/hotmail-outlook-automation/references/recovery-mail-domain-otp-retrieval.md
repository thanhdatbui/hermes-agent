# Quy Tắc Xử Lý Mail Khôi Phục Dạng Mail Domain Riêng Khi Đổi Pass Hotmail

## 1. Bối Cảnh & Sai Lầm Thường Gặp
Khi thực hiện đổi mật khẩu (Change Info) cho tài khoản Hotmail/Outlook trên Microsoft (`account.live.com/password/change`), Microsoft thường kích hoạt xác minh danh tính và yêu cầu gửi mã OTP về **Email khôi phục** (Recovery Email).

Trong farm Taadaa, các tài khoản Hotmail mua từ các shop MMO (BoxTaiKhoan, DongVanFB, TapHoaMMO, CloneFBIG) thường có mail khôi phục mang đuôi domain riêng, ví dụ:
- `@fviainboxes.com`
- `@smvmail.com`
- `@10mail.org`

### 🚨 Pitfall Tai Hại Cần Tránh (User Correction 07/10/2026):
- **Sai lầm của Agent**: Thấy đuôi lạ, tra DNS MX thấy trỏ về server riêng rồi vội vàng thử curl các web tempmail công cộng (`inboxes.com`, `generator.email`). Khi không thấy thư thì vội vàng kết luận: *"Đây là server mail nội bộ kín của shop, bên ngoài không thể đọc được, không lấy được OTP"* $\rightarrow$ Bị User mắng gắt gao: *"Mày vào trang đó chưa? Đkm nó là mail domain chứ có cl gì đâu ?"*.
- **Sự thật**: Đây là dịch vụ **Mail Domain** (hứng thư cho domain riêng do các hệ thống MMO vận hành). Bên bán cung cấp API đọc OTP riêng cho từng loại domain này.

---

## 2. Quy Trình Truy Xuất Mã OTP Mail Domain

### Bước 1: Xác định nguồn mua của tài khoản
Đối soát tài khoản từ file gốc `gmail_clean_v2.xlsx` hoặc lịch sử đơn hàng để biết tài khoản thuộc shop nào:
- **DongVanFB**: Thường dùng các domain như `@smvmail.com`, `@10mail.org`...
- **BoxTaiKhoan / Fviainboxes**: Thường dùng `@fviainboxes.com`.

### Bước 2: Gọi đúng API Mail Domain của nhà cung cấp
- **DongVanFB Mail Domain API**:
  - Endpoint: `GET https://api.dongvanfb.net/user/get_code_mail_domain?apikey=<API_KEY>&email=<EMAIL_KHÔI_PHỤC>`
  - Lưu ý: Dùng endpoint `get_code_mail_domain`, KHÔNG nhầm với `get_code` (vốn chỉ dành cho Hotmail/Facebook thường).
  - Phản hồi mẫu:
    ```json
    {
      "status": true,
      "email": "aerjqjowx@10mail.org",
      "code": "888998"
    }
    ```
- **Khi API báo chưa có thư**:
  - Microsoft gửi mail OTP có thể có độ trễ 5 - 15 giây.
  - Cần retry với khoảng nghỉ 5s, tối đa 6 lần (30s) trước khi kết luận không nhận được mã.

### Bước 3: Phân loại khả thi trước khi thực hiện
1. **Tài khoản có mail khôi phục chính chủ** (vd: `thanhdatbui1995@gmail.com`): Đọc OTP từ hòm thư chính chủ, tỷ lệ thành công 100%.
2. **Tài khoản có mail khôi phục dạng Mail Domain hỗ trợ API**: Gọi API mail domain tương ứng để bóc tách OTP.
3. **Tài khoản trắng mail khôi phục hoặc domain không rõ nguồn**: Nếu không có API đọc hộp thư khôi phục, tài khoản này chỉ nên dùng để phục vụ xác thực Graph API / reg dịch vụ (như TikTok/ChatGPT), tránh cố đổi pass qua web gây khóa tài khoản.
