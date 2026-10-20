# Triage Nguồn Gốc Mua Hotmail & Hàng Đợi Đổi Bảo Mật GPM

## 1. Triage Nguồn Gốc Mua Tài Khoản (OAuth vs Basic Credential)

Khi người dùng thắc mắc: *"Mail này mua bên nào mà không có token API v?"*, TUYỆT ĐỐI KHÔNG lải nhải lý thuyết OAuth hay suy diễn lung tung. Đối soát thẳng dòng tài khoản trong `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (Sheet `Gmail Accounts`):

- **Gói Hotmail OAuth2 (BoxTaiKhoan API Product 60):**
  - Định dạng khi mua: `mail|pass|refresh_token|client_id`.
  - Cột 9 (`token`) chứa chuỗi Refresh Token (dạng `M.C5...`), Cột 10 (`client_id`) chứa UUID app (dạng `9e5f94bc-e8a4-4e73-b...`).
  - Đọc được hộp thư qua Microsoft Graph API mà không cần mở trình duyệt/GPM.

- **Gói Hotmail Cơ Bản / Tool Reg Hàng Loạt (Hòm thư khôi phục `@fviainboxes.com`):**
  - Định dạng khi mua: `mail|pass|mail_khoi_phuc`.
  - Cột 5 (`mail khôi phục`) có đuôi `@fviainboxes.com`.
  - Cột 9 (`token`) và Cột 10 (`client_id`) đều là `None` / rỗng.
  - Thống kê toàn farm: trong 418 tài khoản có mail khôi phục `@fviainboxes.com`, có tới **225 tài khoản mua dạng cơ bản không kèm token OAuth**.
  - **Kết luận dứt khoát:** Mua từ nguồn via/reg hòm thư phụ `@fviainboxes.com`, không mua kèm gói Token API. Cơ chế đọc mail duy nhất là qua session web Outlook trên GPM Profile.

---

## 2. Vì Sao Tài Khoản Đã Lên GPM Lâu Nhưng Chưa Đổi Pass / Change Info?

Khi người dùng thắc mắc: *"Login lên GPM lâu chưa mà chưa được change info v?"*, kiểm tra 2 vị trí:
1. `GPMClient.list_profiles(search=email)`: kiểm tra ngày tạo `created_at` và proxy gán vào profile.
2. File tracker: `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json` (`changed_emails`).

### Điều kiện hợp lệ để vào hàng đợi đổi pass (`gpm_change_hotmail_security.py` / `cron_night_hotmail_security_watchdog.py`):
1. **Domain:** Thuộc Microsoft (`@hotmail.`, `@outlook.`, `@live.`, `@msn.`).
2. **TikTok State:** Đã reg TikTok thành công (Cột 3 User và Cột 4 Pass TikTok trong `taikhoan_dat_v2_updated .xlsx` có dữ liệu).
3. **ChatGPT State:** Đã từng reg ChatGPT (Cột 12 `PASS CHATGPT` có dữ liệu).
4. **Độ tuổi tài khoản:** Ngâm $\ge$ 7 ngày (tính từ ngày tạo ở Cột 9).
5. **Khoalee Filter:** TUYỆT ĐỐI BỎ QUA tài khoản dính mail khôi phục chứa từ khóa `khoa` (`khoaleemagic@gmail.com`...).
6. **Proxy Consistency:** Profile GPM phải khớp đúng cổng proxy của máy thật (ví dụ Máy 38 bắt buộc proxy `192.168.110.2:20038`). Profile gán proxy cũ hoặc proxy chung (như MikroTik `10006`) sẽ bị bỏ qua.

### Nguyên nhân trễ / chưa đổi info dù profile đã tạo lâu:
- **Cơ chế cuốn chiếu an toàn:** Watchdog đêm chỉ đổi **1–3 tài khoản mỗi lượt** sau ca 4 đêm để tránh bão checkpoint IP / block hàng loạt. Hệ thống đổi theo thứ tự hàng đợi (đã đổi thành công 81+ tài khoản).
- **Lệch proxy profile:** Profile tạo từ lâu nhưng gán proxy cũ/lệch máy thì script bỏ qua. Chỉ khi profile được tạo lại/gán chuẩn proxy máy thật (ví dụ đổi sang `20038`), tài khoản mới được đưa vào hàng đợi cuốn chiếu.
