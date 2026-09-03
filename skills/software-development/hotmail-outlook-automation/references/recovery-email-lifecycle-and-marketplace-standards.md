# Recovery Email Lifecycle & Marketplace Standards (MMO Farm)

## 1. Full Takeover Scope (4 Bước bảo vệ tài khoản toàn diện)
Đổi mật khẩu chỉ là bước đầu tiên trong quy trình bảo vệ tài khoản. Quy trình takeover đầy đủ gồm:
1. **Change/Reset Password:** Đổi mật khẩu mạnh ngẫu nhiên theo chuẩn Microsoft.
2. **Sign Out Everywhere (Logout all devices):** Vô hiệu hóa toàn bộ session token, cookie, và app login cũ trên mọi thiết bị trong 24h.
3. **Security Proofs Verification / Cleanup:** Kiểm tra và gán/xóa mail khôi phục theo từng giai đoạn.
4. **App & Inventory Sync:** Cập nhật mật khẩu mới vào Outlook app trên máy farm và ghi đè Excel (`gmail_clean_v2.xlsx`) kèm backup.

---

## 2. Recovery Email Lifecycle (Nuôi Farm vs Xuất Bán)

### Giai đoạn 1: Nuôi Farm (30 – 60 ngày) — BẮT BUỘC GẮN MAIL KP
* **Cứu Checkpoint:** Trong quá trình chạy proxy đổi IP và nhận OTP TikTok, Microsoft thường xuyên checkpoint khóa tạm. Có Mail KP (`thanhdatbui1995@gmail.com`) mới khôi phục được mật khẩu và cứu kênh.
* **Chống Shop Cũ Back Acc:** Ngăn chặn người bán ban đầu dùng mail khôi phục gốc để lấy lại tài khoản.

### Giai đoạn 2: Xuất Bán Cho Khách — GỠ BỎ MAIL KP CÁ NHÂN
* **Bảo vệ quyền riêng tư:** Tránh việc khách login/resend mã làm rác Gmail cá nhân hoặc khách nghi ngờ bị back nick.
* **Quy tắc gỡ Mail KP của Microsoft:**
  - Khi tài khoản **chưa bật 2FA**: Vào Security $\rightarrow$ Xóa/Thay thế Mail KP $\rightarrow$ Nhập OTP gửi về Mail KP hiện tại $\rightarrow$ **Mail KP được gỡ NGAY LẬP TỨC** (không cần chờ ngày nào).
  - **Lưu ý bẫy 30 ngày (Pending 30 days):** Microsoft **chỉ ép chờ 30 ngày** khi chọn *"Tôi không còn quyền truy cập vào các thông tin này"* (mất mail KP). Khi tự bấm Xóa và xác nhận bằng OTP thì có hiệu lực tức thì.
  - **Thời điểm gỡ:** Thực hiện tự động ngay trong ngày chốt đơn xuất bán trước khi giao list cho khách.

---

## 3. Khảo Sát Định Dạng Bàn Giao Thị Trường (BoxTaiKhoan & Bot Shop MMO)

| Loại tài khoản | Định dạng bàn giao chuẩn | Đặc điểm Mail KP |
| :--- | :--- | :--- |
| **Kênh TikTok có Shop/Live** | `User TT \| Pass TT \| Hotmail \| Pass Hotmail` | ❌ **Không kèm Mail KP** (khách chỉ cần login Hotmail lấy OTP 1 lần để đổi info TikTok) |
| **Hotmail Trusted Live 3-6M** | `Mail \| Pass \| Refresh_Token` | ❌ Đọc code qua OAuth2 Graph API, không cần Mail KP |
| **Hotmail Trusted GraphAPI** | `Mail \| Pass \| MailKP Domain (@fviainboxes)` | ⚠️ Mail KP web tạm miễn phí, không phải Gmail cá nhân |
| **Outlook/Hotmail Zin 12-36M** | `Mail \| Pass \| Refresh_Token` (Skip 7 ngày) | ❌ Cho phép login thẳng không đòi xác minh |
