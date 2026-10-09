# Hotmail Security & Anti-Back Workflow: Mail Khôi Phục Domain Riêng

## 1. Bối cảnh & Mục đích Nghiệp Vụ
- **Mục đích:** Hotmail được nuôi/ngâm trên GPM đủ tuổi (>= 7 ngày) sau đó đổi pass và xử lý bảo mật để **bán kèm với tài khoản TikTok** giao cho khách hàng (khách dùng Hotmail để login TikTok).
- **Yêu cầu bàn giao:** Không bật 2FA TOTP (Microsoft Authenticator) trên Hotmail vì khách hàng thông thường không biết dùng app 2FA, dễ gây khiếu nại/nghẽn support.
- **Rủi ro bên bán back:** Khi Hotmail dùng mail khôi phục dạng domain tạm (`@fviainboxes.com`, `@smvmail.com`...), bên bán cũ có thể bấm "Forgot password" và vào trang domain đọc OTP để cướp lại acc nếu vẫn giữ mail khôi phục cũ.

## 2. Giải Pháp Triệt Để: Thay Mail Random Trên Domain
Để triệt hạ khả năng bên bán back acc mà vẫn giữ luồng bàn giao tiện lợi cho khách:
1. **Tạo mail khôi phục random mới:**
   - Gen định dạng độc nhất: `kbtad_<8_random_chars>@fviainboxes.com` (ví dụ: `kbtad_utpq8wmi@fviainboxes.com`).
2. **Thêm phương thức bảo mật mới trên Microsoft:**
   - Truy cập `https://account.live.com/proofs/manage/additional`.
   - Bấm *Add another way to sign in to your account* -> Chọn *Email a code*.
   - Nhập mail khôi phục random mới -> Bấm *Next*.
   - Gọi API `https://fviainboxes.com/messages?username=<user>&domain=fviainboxes.com` để lấy mã bảo mật (6 số).
   - Điền OTP để kích hoạt mail khôi phục mới.
3. **Xóa vĩnh viễn mail khôi phục cũ của bên bán:**
   - Microsoft chỉ cho phép xóa mail khôi phục khi đã có ít nhất 1 phương thức bảo mật thay thế.
   - Bấm mở pullout container của mail cũ của shop -> Bấm **Remove** -> Xác nhận Remove trên dialog.
4. **Đá sạch mọi phiên đăng nhập cũ (Sign out everywhere):**
   - Bấm liên kết `Sign out everywhere` (`#DeleteTrustedDevices`) -> Xác nhận trên modal để revoke toàn bộ OAuth tokens / trusted devices của bên bán trong 24h.
5. **Cập nhật dữ liệu:**
   - Cập nhật mail khôi phục mới vào Cột 5 của `gmail_clean_v2.xlsx`.
   - Cập nhật vào tracker `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json`.

## 3. Cơ Chế Chống Back Hoạt Động Thế Nào?
- Khi bên bán bấm "Forgot password" tại `login.live.com`, Microsoft hiển thị dạng che: `kb*****@fviainboxes.com` và **bắt buộc người dùng phải gõ chính xác 100% toàn bộ địa chỉ email khôi phục mới** mới chịu gửi mã.
- Bên bán chỉ biết địa chỉ cũ của nó, hoàn toàn không biết chuỗi random mới -> Microsoft báo lỗi sai email và chặn đứng gửi mã, acc an toàn tuyệt đối.

## 4. API & Script Tham Chiếu
- Helper lấy OTP: `D:\Taadaa\Hotmail\scripts\mail_domain_otp_helper.py`
- Endpoints `fviainboxes.com`:
  - List: `GET https://fviainboxes.com/messages?username={username}&domain={domain}`
  - Detail: `GET https://fviainboxes.com/message?username={username}&domain={domain}&id={id}`
