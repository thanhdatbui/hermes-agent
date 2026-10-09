# Quy trình Tối Ưu: Ngâm 7 Ngày Hotmail Đổi Pass Chrome Rồi Mới Log Outlook

## 1. Bản Chất Kiến Trúc Vận Hành (Đã Tham Vấn Sol GPT-5.6 High 18/09/2026)
- **Cơ chế tuổi tài khoản Microsoft (MSA Trust):** Microsoft Account không có yêu cầu bắt buộc phải cài và đăng nhập App Outlook trên Android thì mới tính tuổi tài khoản hay tính độ uy tín thiết bị. Tuổi và độ uy tín được tính dựa trên thời gian tài khoản tồn tại, IP/proxy cố định, không có các hành vi đổi thông tin dồn dập.
- **Phản biện tối ưu của Operator:**
  - *Luồng cũ bất hợp lý:* Ngày 0 log Outlook pass cũ -> Ngâm 7 ngày -> Mở Chrome đổi pass mới + bấm Sign out everywhere -> App Outlook bị revoke session và đá văng -> Phải tốn công đi đăng nhập Outlook lần 2 bằng pass mới.
  - *Luồng mới tinh gọn:* **NGÂM 7 NGÀY TRÊN HỆ THỐNG -> ĐỦ 7 NGÀY ĐỔI PASS TRÊN CHROME (ĐÁ SẠCH BÊN BÁN) -> RỒI MỚI ĐĂNG NHẬP APP OUTLOOK 1 LẦN DUY NHẤT BẰNG PASS MỚI.**

## 2. Nuôi TikTok Trong 7 Ngày Đầu Có Ảnh Hưởng Không?
- **HOÀN TOÀN KHÔNG ẢNH HƯỞNG:**
  - Tài khoản TikTok sau khi Add 2FA đã có bộ định danh độc lập: **Mật khẩu TikTok mạnh + Mã 2FA TOTP (Secret Key 32 ký tự)**.
  - Quá trình chạy lướt feed, tương tác, upload video diễn ra hoàn toàn trên app TikTok, không cần đụng đến mailbox Hotmail.
  - Nếu trong 7 ngày đầu TikTok phát sinh nhu cầu đọc OTP đột xuất: Dùng **Microsoft Graph API đọc ngầm trực tiếp qua `refresh_token`** mà không cần app Outlook.

## 3. Quy Trình Vận Hành Chuẩn Hóa Toàn Farm (4 Giai Đoạn)

### Giai đoạn 1: Gán Hotmail & Kích Hoạt Nuôi (Ngày 0)
1. Mua Hotmail mới qua API shop (`buy_hotmail.py`) có đủ `email|pass|refresh_token|client_id`.
2. Đổi email liên kết TikTok sang Hotmail mới (xác thực OTP qua Graph API).
3. Tuyệt đối **CHƯA ĐĂNG NHẬP APP OUTLOOK** và **CHƯA ĐỔI PASS HOTMAIL** lúc này.

### Giai đoạn 2: Giữ Trạng Thái Ngâm Ổn Định (Ngày 1 -> Ngày 7)
- Để tài khoản chạy bình thường theo các ca nuôi của farm.
- Không thực hiện các hành động nhạy cảm trên tài khoản Hotmail để tránh kích hoạt checkpoint của Microsoft.

### Giai đoạn 3: Đổi Mật Khẩu Hotmail & Đá Sạch Bên Bán (Sau Ngày 7)
1. Mở Web Chrome trên đúng máy S7 đó (dùng Proxy 4G của máy).
2. Vào `account.live.com/password/change` -> Nhập mật khẩu cũ của bên bán -> Đổi sang mật khẩu ngẫu nhiên mạnh mới của farm (`generate_account_password`).
3. Gỡ email khôi phục rác của bên bán nếu có.
4. Bấm **"Đăng xuất ở mọi nơi" (Sign out everywhere)** để thu hồi toàn bộ token cũ, cắt đứt vĩnh viễn quyền truy cập của bên bán.
5. Cập nhật mật khẩu mới vào **Cột G (`PASS_MAIL`)** của file Excel `taikhoan_dat_v2_updated .xlsx`.
6. Ghi log hoàn thành vào `.ai-runs/hotmail-change-info/` hoặc state file để không bao giờ đổi đè lại (Idempotency).

### Giai đoạn 4: Đăng Nhập App Outlook Lần Đầu & Duy Nhất (Chốt Hạ)
1. Khóa cứng hướng màn hình dọc chuẩn (Portrait 1080x1920):
   ```bash
   content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
   content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
   ```
2. Mở App Outlook (`com.microsoft.office.outlook`).
3. Nhập Email và **Mật khẩu Mới vừa đổi**.
4. Hoàn tất đăng nhập và vào Hộp thư đến (Inbox) -> Giữ phiên chính chủ sạch sẽ trên máy, sẵn sàng bàn giao xuất xưởng cho khách.
