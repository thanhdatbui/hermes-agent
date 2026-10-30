# Admin Farm Hotmail Graph Token Dual-Workbook Resolution & GPM Fallback

## 1. Triệu Chứng & Cảnh Báo P0 Giả (False Alarm)
Khi ca nuôi feed chạy đến hàng tài khoản chưa có trên máy (ví dụ Row 4 `@huynhthiloan112` trên Máy 270):
- Thiết bị dừng tại màn hình One-Tap Login ("Chào mừng bạn trở lại") với 3 nick cũ vẫn nguyên vẹn.
- Watchdog bắt trúng marker `login/account screen detected` và kích hoạt alert P0 báo động văng phiên.
- Hệ thống kích hoạt auto-login recovery (`tiktok_login_v1.py` 420s + `reconcile_tiktok_accounts.py` 600s) nhưng cả 2 đều chết timeout (tổng 17 phút).

## 2. Bẫy Đối Soát Dữ Liệu Excel (Agent Pitfall)
- **Cấu trúc cột `taikhoan_dat_v2_updated .xlsx`**:
  - Cột 1 (`A`): Máy
  - Cột 2 (`B`): Slot / Tik
  - Cột 3 (`C`): TikTok ID
  - Cột 4 (`D`): `PASS` (Mật khẩu TikTok tĩnh)
  - Cột 5 (`E`): `2FA`
  - Cột 6 (`F`): `GMAIL` / `HOTMAIL`
  - Cột 7 (`G`): `PASS MAIL`
- **Lưu ý tối quan trọng**:
  - Với dàn Admin (Máy 201–280), phần lớn nick được đăng ký bằng Hotmail qua luồng mã xác minh Email OTP, nên cột `PASS` (Cột 4) là `None`.
  - **CẤM TUYỆT ĐỐI** đọc nhầm Cột 4 (`PASS = None`) thành thiếu Email. Nick có đầy đủ Cột 6 (`GMAIL/HOTMAIL`) và Cột 7 (`PASS MAIL`) là nick hoàn toàn hợp lệ (`usable = True`).

## 3. Nguyên Nhân Gốc Gây Timeout Auto-Login (Dual-Cluster Token Drift)
1. **Lệch file sổ cái token Microsoft Graph API**:
   - Trong `D:/Taadaa/Tiktok_Reg/hotmail_provider.py`, hàm `resolve_graph_credentials(email)` mặc định fallback về:
     ```python
     workbook = str(Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"))
     ```
   - Đối với tài khoản dàn Admin (máy $\ge 200$), Refresh Token lưu tại:
     `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` (Cột 9: `token`, Cột 10: `client_id`).
   - Kết quả: `resolve_graph_credentials` không tìm thấy token trong file Kibe, trả về `(None, None)` và ngộ nhận mailbox chưa có token.
2. **Kẹt nhánh fallback**:
   - Khi `rt is None`, script bỏ qua luồng Graph API (PC-side).
   - Tiếp tục rơi vào nhánh fallback mở app Outlook trên thiết bị Android S7 cũ hoặc timeout đợi thư, trong khi lẽ ra chỉ mất 1 giây để lấy mã qua Graph API trên PC.
3. **Hiện trạng Profile GPM**:
   - Các tài khoản Hotmail Admin đều có Profile GPM tương ứng (tên dạng `270 - <email> - <port>`).
   - Module `read_tiktok_otp_from_gpm_profile` trong `D:/Taadaa/Hotmail/scripts/read_otp_gpm.py` đã hỗ trợ Playwright CDP duyệt 2 tab (Ưu tiên / Khác), nhưng chỉ được gọi khi luồng resend OTP kích hoạt.

## 4. Kiểm Chứng & Khắc Phục Chuẩn
1. **Kiểm tra tính sống của Refresh Token (O(1) Python check)**:
   ```python
   import requests
   res = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data={
       "client_id": cid,
       "grant_type": "refresh_token",
       "refresh_token": rt,
       "scope": "https://graph.microsoft.com/Mail.Read offline_access"
   }, timeout=10)
   # res.status_code == 200 -> Token LIVE, cấp access_token mới ngay lập tức
   ```
2. **Quy chuẩn cấu hình môi trường khi gọi login cụm Admin**:
   Khi gọi `tiktok_login_v1.py` hoặc các flow cứu hộ cho máy $\ge 200$, bắt buộc inject:
   ```python
   env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"
   env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
   env["HOTMAIL_WORKBOOK"] = r"D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx"
   ```
3. **Chuẩn hóa `resolve_graph_credentials`**:
   Hỗ trợ quét cả 2 file `kibe/gmail_clean_v2.xlsx` và `admin/gmail_clean_v2.xlsx` nếu không tìm thấy ở file đầu tiên, đảm bảo tự động lấy mã OTP trong 1s cho toàn bộ 160 máy cả 2 cụm.
