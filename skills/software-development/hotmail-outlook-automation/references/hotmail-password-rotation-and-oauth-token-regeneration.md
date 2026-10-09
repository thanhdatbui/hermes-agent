# Đổi Pass Hotmail Sớm & Cơ Chế Sinh Lại OAuth Refresh Token Trên Thiết Bị S7 (17/09/2026)

## 1. Bối Cảnh & Tư Duy Vận Hành Cốt Lõi (User Directive 17/09/2026)
- **Rủi ro chí mạng khi nuôi TikTok lâu:**
  - Hotmail mua từ các shop bên ngoài có sẵn tài khoản + mật khẩu gốc + mail khôi phục cũ (Getnada/mail rác).
  - Nếu không đổi mật khẩu Hotmail sớm ngay sau khi mua/reg TikTok, sau 2–4 tuần nuôi acc lên tương tác cao, bên bán mail có thể dùng pass cũ/mail khôi phục để back lại hộp thư $\rightarrow$ bấm "Quên mật khẩu" chiếm đoạt toàn bộ nick TikTok của farm.
  - **Quy tắc bắt buộc:** Phải đổi mật khẩu Hotmail và gỡ sạch mail khôi phục của bên bán sớm nhất có thể.

- **Vấn đề kỹ thuật khi đổi Pass Hotmail:**
  - Đổi pass Hotmail khiến toàn bộ chuỗi `refresh_token` Graph API cũ (dùng đọc OTP) bị Microsoft **revoke (hủy hiệu lực)** ngay lập tức.
  - Microsoft chặn triệt để luồng ROPC (`grant_type=password`) trên tài khoản cá nhân (Personal/Consumer MSA: Hotmail/Outlook.com), đồng thời chặn các request web login gửi từ IP lạ không có session/proxy hợp lệ (báo lỗi `ConvergedError: We received a bad request` hoặc checkpoint khóa tạm thời).

---

## 2. Cơ Chế Sinh Lại Refresh Token Tự Động Qua Chrome Trên Thiết Bị S7

### A. Tận Dụng Môi Trường Thiết Bị S7
- Thiết bị S7 trong farm luôn chạy qua **Proxy 4G chuyên biệt** của từng máy (đã kết nối VPN `tun0`).
- Trình duyệt Chrome trên S7 (`com.android.chrome`) được Microsoft tin cậy về dấu vân tay thiết bị (device fingerprint) và IP.

### B. Quy Trình Cấp Lại Token Tự Động:
1. **Mở URL OAuth Authorize trên Chrome thiết bị:**
   ```text
   https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=9e5f94bc-e8a4-4e73-b8be-63364c29d753&response_type=code&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient&scope=https://graph.microsoft.com/Mail.Read%20offline_access&prompt=login&login_hint=<EMAIL>
   ```
   *(Client ID chuẩn của shop: `9e5f94bc-e8a4-4e73-b8be-63364c29d753`)*

2. **Tự Động Tương Tác Qua UI Automator:**
   - Điền mật khẩu mới vào form đăng nhập (`idSIButton9`).
   - Xử lý màn hình "Duy trì đăng nhập?" (Stay signed in? / KMSI) $\rightarrow$ Tap "Có / Yes".
   - Xử lý màn hình cấp quyền (Consent: "Cho phép ứng dụng này truy cập thông tin...") $\rightarrow$ Tap "Có / Accept" (`idBtn_Accept`).

3. **Bắt Mã `code` Từ Thanh Địa Chỉ Chrome:**
   - Sau khi chấp thuận, Chrome redirect về:
     `https://login.microsoftonline.com/common/oauth2/nativeclient?code=M.C546_BAY...`
   - Script dump UI XML, đọc thuộc tính `text` của thanh địa chỉ (`com.android.chrome:id/url_bar`) để trích xuất giá trị tham số `code`.

4. **Đổi `code` Lấy `refresh_token` Mới Qua Endpoint Microsoft:**
   - Gửi POST tới `https://login.microsoftonline.com/common/oauth2/v2.0/token`:
     ```python
     data = {
         "client_id": "9e5f94bc-e8a4-4e73-b8be-63364c29d753",
         "grant_type": "authorization_code",
         "code": auth_code,
         "redirect_uri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
         "scope": "https://graph.microsoft.com/Mail.Read offline_access",
     }
     r = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
     token_data = r.json()
     new_refresh_token = token_data["refresh_token"]
     ```

5. **Xác Thực (DoD) & Cập Nhật Dữ Liệu:**
   - Dùng ngay `new_refresh_token` gọi Microsoft Graph API `https://graph.microsoft.com/v1.0/me/messages` qua `scripts/test_graph_token.py`.
   - Xác nhận bóc tách được tin nhắn chứa mã OTP 6 số của TikTok.
   - Ghi đè mật khẩu mới và chuỗi `refresh_token` mới vào database / file Excel của farm.
