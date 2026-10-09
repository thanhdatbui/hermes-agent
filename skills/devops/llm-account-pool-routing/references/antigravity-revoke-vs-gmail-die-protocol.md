# Antigravity Revoke vs Gmail Die & Re-Auth Protocol (2026-09-20)

## 1. Bản chất của Revoke (`invalid_grant: Refresh token rejected`)
- **Revoke token**: Đây là Google OAuth thu hồi quyền truy cập của App Client Antigravity (hoặc hết hạn token), **KHÔNG** đồng nghĩa với tài khoản Gmail bị DIE.
- Session Google trong profile GPM có thể chỉ bị văng đăng xuất hoặc đổi IP proxy khiến token bị vô hiệu hóa, nhưng tài khoản Gmail (Email, Password, TOTP 2FA) vẫn LIVE 100%.
- Tuyệt đối không xóa nick khỏi Excel hoặc vội kết luận nick chết khi chỉ thấy OmniRoute báo revoked.

## 2. Quy trình chuẩn phục hồi & Đăng nhập lại GPM
1. **Bắt buộc Check-live trước khi login**:
   - Dùng canonical runner `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py` (sử dụng engine `checkmail.live` qua mobile proxy farm).
   - Chỉ tài khoản nào trả về `die`/`disabled` thật mới dọn dẹp. Tài khoản `live` giữ nguyên để nạp lại session.
2. **Tuổi tài khoản ngâm >= 7 ngày (Tránh bẫy ngày checklive)**:
   - Khi lọc candidates đăng nhập trong `post_evening_gpm_login_watchdog.py`, **CẤM** đọc cột `Cập Nhật` (cột 15) của `master_gmail_manager.xlsx` vì đó là timestamp của lần quét checklive gần nhất (dễ bị tính thành 0 ngày tuổi và loại nhầm).
   - Bắt buộc tra cứu ngày tạo gốc tại cột `ngày tạo` (cột 7 / index 6) của file `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
3. **Mở rộng Time Window chạy tự động**:
   - Bên cạnh ca tối (`20:15 - 23:45`), watchdog cần được cấu hình mở thêm khung giờ máy rảnh ban ngày (Sáng `07:15 - 08:45`, Trưa `12:00 - 13:45`) để cuốn chiếu xử lý khi máy S7 rảnh giữa các ca nuôi feed.
4. **Vượt màn hình cảnh báo Google OAuth Antigravity**:
   - Khi Google hiển thị cảnh báo: *"Đảm bảo rằng bạn đã tải ứng dụng này xuống từ Google. Đừng đăng nhập vào Google Antigravity trừ phi bạn chắc chắn..."*.
   - Nút xác nhận tiếp tục thực chất có nhãn text là `Đăng nhập` (hoặc `Tiếp tục` / `Continue`).
   - Click `button:has-text("Đăng nhập")` sẽ kích hoạt callback redirect về `http://127.0.0.1:20129/callback?code=...`.
